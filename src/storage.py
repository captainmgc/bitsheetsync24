from typing import Any, Dict, Optional
import hashlib
from datetime import datetime

from sqlalchemy import create_engine, Table, Column, MetaData, BigInteger, Text, JSON, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine
from sqlalchemy.sql import text

from src.config import DATABASE_URL

metadata = MetaData(schema="bitrix")

# We'll operate via raw SQL for ON CONFLICT upsert to be explicit

def get_engine() -> Engine:
    return create_engine(DATABASE_URL, pool_pre_ping=True)


def json_hash(data: Dict[str, Any]) -> str:
    # stable hash of JSON to detect changes
    import json
    s = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def choose_updated_at(item: Dict[str, Any]) -> Optional[datetime]:
    candidates = [
        item.get("DATE_MODIFY"),
        item.get("DATE_UPDATE"),
        item.get("UPDATED_TIME"),
        item.get("CHANGED_DATE"),
        item.get("LAST_UPDATED"),
    ]
    for v in candidates:
        if v:
            try:
                # Bitrix usually returns ISO 8601 or 'YYYY-MM-DD HH:MM:SS'
                from dateutil import parser  # type: ignore
                return parser.parse(v)
            except Exception:
                try:
                    return datetime.fromisoformat(v)
                except Exception:
                    continue
    return None


UPSERT_SQL = {
    "leads": """
    INSERT INTO bitrix.leads (id, data, updated_at, fetched_at, source_hash)
    VALUES (:id, CAST(:data AS JSONB), :updated_at, now(), :source_hash)
    ON CONFLICT (id) DO UPDATE SET
      data = EXCLUDED.data,
      updated_at = EXCLUDED.updated_at,
      fetched_at = now(),
      source_hash = EXCLUDED.source_hash
    """,
    "contacts": """
    INSERT INTO bitrix.contacts (id, data, updated_at, fetched_at, source_hash)
    VALUES (:id, CAST(:data AS JSONB), :updated_at, now(), :source_hash)
    ON CONFLICT (id) DO UPDATE SET
      data = EXCLUDED.data,
      updated_at = EXCLUDED.updated_at,
      fetched_at = now(),
      source_hash = EXCLUDED.source_hash
    """,
    "deals": """
    INSERT INTO bitrix.deals (id, data, updated_at, fetched_at, source_hash)
    VALUES (:id, CAST(:data AS JSONB), :updated_at, now(), :source_hash)
    ON CONFLICT (id) DO UPDATE SET
      data = EXCLUDED.data,
      updated_at = EXCLUDED.updated_at,
      fetched_at = now(),
      source_hash = EXCLUDED.source_hash
    """,
    "activities": """
    INSERT INTO bitrix.activities (id, data, updated_at, fetched_at, source_hash)
    VALUES (:id, CAST(:data AS JSONB), :updated_at, now(), :source_hash)
    ON CONFLICT (id) DO UPDATE SET
      data = EXCLUDED.data,
      updated_at = EXCLUDED.updated_at,
      fetched_at = now(),
      source_hash = EXCLUDED.source_hash
    """,
    "tasks": """
    INSERT INTO bitrix.tasks (id, data, updated_at, fetched_at, source_hash)
    VALUES (:id, CAST(:data AS JSONB), :updated_at, now(), :source_hash)
    ON CONFLICT (id) DO UPDATE SET
      data = EXCLUDED.data,
      updated_at = EXCLUDED.updated_at,
      fetched_at = now(),
      source_hash = EXCLUDED.source_hash
    """,
    "task_comments": """
    INSERT INTO bitrix.task_comments (id, task_id, data, updated_at, fetched_at, source_hash)
    VALUES (:id, :task_id, CAST(:data AS JSONB), :updated_at, now(), :source_hash)
    ON CONFLICT (id) DO UPDATE SET
      data = EXCLUDED.data,
      updated_at = EXCLUDED.updated_at,
      fetched_at = now(),
      source_hash = EXCLUDED.source_hash
    """,
    "users": """
    INSERT INTO bitrix.users (id, data, updated_at, fetched_at, source_hash)
    VALUES (:id, CAST(:data AS JSONB), :updated_at, now(), :source_hash)
    ON CONFLICT (id) DO UPDATE SET
      data = EXCLUDED.data,
      updated_at = EXCLUDED.updated_at,
      fetched_at = now(),
      source_hash = EXCLUDED.source_hash
    """,
    "departments": """
    INSERT INTO bitrix.departments (id, data, updated_at, fetched_at, source_hash)
    VALUES (:id, CAST(:data AS JSONB), :updated_at, now(), :source_hash)
    ON CONFLICT (id) DO UPDATE SET
      data = EXCLUDED.data,
      updated_at = EXCLUDED.updated_at,
      fetched_at = now(),
      source_hash = EXCLUDED.source_hash
    """,
}


def upsert_entity(entity: str, item: Dict[str, Any], engine: Optional[Engine] = None, task_id: Optional[int] = None):
    import json as json_lib
    eng = engine or get_engine()
    with eng.begin() as conn:
        uid = int(item.get("ID") or item.get("id"))
        u_at = choose_updated_at(item)
        s_hash = json_hash(item)
        params = {
            "id": uid,
            "data": json_lib.dumps(item, ensure_ascii=False),  # Convert dict to JSON string
            "updated_at": u_at,
            "source_hash": s_hash,
        }
        if entity == "task_comments":
            params["task_id"] = task_id or int(item.get("TASK_ID") or 0)
        conn.execute(text(UPSERT_SQL[entity]), params)
