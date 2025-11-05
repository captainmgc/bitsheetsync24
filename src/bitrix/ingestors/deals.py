from typing import Optional
from datetime import datetime
import logging
from src.bitrix.client import BitrixClient
from src.storage import upsert_entity, get_engine
from sqlalchemy.sql import text

logger = logging.getLogger(__name__)

SELECT_FIELDS = [
    "ID","TITLE","STAGE_ID","CATEGORY_ID","OPPORTUNITY","CURRENCY_ID","ASSIGNED_BY_ID",
    "DATE_CREATE","DATE_MODIFY","CONTACT_ID","COMPANY_ID"
]

def full_sync(client: BitrixClient, limit: Optional[int] = None) -> int:
    count = 0
    for item in client.list_paginated("crm.deal.list", select=SELECT_FIELDS, order={"ID": "ASC"}, include_total=True):
        upsert_entity("deals", item)
        count += 1
        if limit and count >= limit:
            break
    _update_sync_state(count, is_full=True)
    return count


def incremental_sync(client: BitrixClient, since: Optional[datetime] = None, limit: Optional[int] = None) -> int:
    """
    Sync only deals that were created or modified since last sync.
    Uses LOGIC=OR with >DATE_CREATE and >DATE_MODIFY filters to catch both new and updated records.
    """
    if since is None:
        since = _get_last_sync()
    
    if since is None:
        logger.info("No previous sync found, running full sync")
        return full_sync(client, limit)
    
    since_str = since.strftime('%Y-%m-%dT%H:%M:%S')
    logger.info(f"Incremental sync for deals created or modified since {since_str}")
    
    # Catch both new (>DATE_CREATE) and updated (>DATE_MODIFY) records
    filter_params = {
        "LOGIC": "OR",
        ">DATE_CREATE": since_str,
        ">DATE_MODIFY": since_str
    }
    
    count = 0
    for item in client.list_paginated(
        "crm.deal.list",
        select=SELECT_FIELDS,
        order={"ID": "ASC"},
        filter=filter_params,
        include_total=True
    ):
        upsert_entity("deals", item)
        count += 1
        if limit and count >= limit:
            break
    
    _update_sync_state(count, is_full=False)
    logger.info(f"Incremental sync completed: {count} deals")
    return count


def _get_last_sync() -> Optional[datetime]:
    try:
        eng = get_engine()
        with eng.connect() as conn:
            result = conn.execute(text(
                "SELECT last_sync_at FROM bitrix.sync_state WHERE entity = 'deals'"
            )).fetchone()
            return result[0] if result else None
    except Exception:
        return None


def _update_sync_state(count: int, is_full: bool):
    try:
        eng = get_engine()
        with eng.begin() as conn:
            if is_full:
                conn.execute(text("""
                    INSERT INTO bitrix.sync_state (entity, last_sync_at, last_full_sync_at, record_count, status)
                    VALUES ('deals', now(), now(), :count, 'completed')
                    ON CONFLICT (entity) DO UPDATE SET
                        last_sync_at = now(),
                        last_full_sync_at = now(),
                        record_count = :count,
                        status = 'completed',
                        updated_at = now()
                """), {"count": count})
            else:
                conn.execute(text("""
                    INSERT INTO bitrix.sync_state (entity, last_sync_at, record_count, status)
                    VALUES ('deals', now(), :count, 'completed')
                    ON CONFLICT (entity) DO UPDATE SET
                        last_sync_at = now(),
                        record_count = COALESCE(bitrix.sync_state.record_count, 0) + :count,
                        status = 'completed',
                        updated_at = now()
                """), {"count": count})
    except Exception:
        pass
