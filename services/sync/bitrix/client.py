import os
import time
from typing import Dict, Iterable, List, Optional, Tuple

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type

from dotenv import load_dotenv

load_dotenv()

BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL", "").rstrip("/")

class BitrixError(Exception):
    pass

class BitrixClient:
    def __init__(self, base_url: Optional[str] = None, timeout: float = 20.0):
        self.base_url = (base_url or BITRIX_WEBHOOK_URL).rstrip("/")
        if not self.base_url:
            raise ValueError("BITRIX_WEBHOOK_URL is not configured")
        self.timeout = timeout
        self._client = httpx.Client(timeout=self.timeout)

    def _method_url(self, method: str) -> str:
        return f"{self.base_url}/{method}.json"

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_exponential_jitter(initial=0.5, max=5.0),
        retry=retry_if_exception_type((httpx.HTTPError, BitrixError)),
    )
    def call(self, method: str, data: Optional[Dict] = None) -> Dict:
        url = self._method_url(method)
        try:
            resp = self._client.post(url, data=data or {})
            resp.raise_for_status()
            j = resp.json()
        except httpx.HTTPError as e:
            raise
        except Exception as e:
            raise BitrixError(f"Invalid JSON from {url}: {e}")

        if "error" in j:
            # Bitrix style error
            raise BitrixError(f"{j.get('error')}: {j.get('error_description')}")
        return j

    def list_paginated(self, method: str, select: Optional[List[str]] = None, order: Optional[Dict] = None,
                       filter: Optional[Dict] = None, page_start: int = 0, page_size_hint: int = 50,
                       include_total: bool = True):
        """
        Iterate over list responses using Bitrix 'start' pagination.
        Returns a generator of items and optional total count when available.
        """
        start = page_start
        total: Optional[int] = None
        first = True

        while True:
            payload: Dict = {}
            if select:
                for s in select:
                    payload.setdefault('select[]', [])
                # httpx automatically encodes lists; we can just pass select as list under key 'select[]'
                payload['select[]'] = select
            if order:
                for k, v in order.items():
                    payload[f"order[{k}]"] = v
            if filter:
                for k, v in filter.items():
                    payload[f"filter[{k}]"] = v
            payload['start'] = start
            if include_total and first:
                payload['count_total'] = 1

            j = self.call(method, payload)

            # Handle both flat result:[] and nested result:{tasks:[], total:X, next:Y}
            result_data = j.get('result', [])
            
            # total available only sometimes and only on first page typically
            if first:
                # Check both top-level and nested total
                total = j.get('total') if isinstance(j.get('total'), int) else None
                if total is None and isinstance(result_data, dict):
                    total = result_data.get('total') if isinstance(result_data.get('total'), int) else None
                # expose for monitoring
                try:
                    self.last_total = total
                except Exception:
                    pass
                first = False

            # Extract items from result (list or dict with 'tasks' key)
            if isinstance(result_data, list):
                items = result_data
            elif isinstance(result_data, dict):
                # tasks.task.list returns {result: {tasks: [...], total: X, next: Y}}
                items = result_data.get('tasks', result_data.get('items', []))
            else:
                items = []
            if not items:
                break

            for it in items:
                yield it

            # continue by 'next' or by len(items) advancing start
            # check both top-level and nested 'next'
            next_val = j.get('next')
            if next_val is None and isinstance(result_data, dict):
                next_val = result_data.get('next')
            
            if next_val is not None:
                start = next_val
            else:
                start = int(start) + len(items)

            # If total known and we've iterated enough, stop
            if total is not None and start >= total:
                break

        return

