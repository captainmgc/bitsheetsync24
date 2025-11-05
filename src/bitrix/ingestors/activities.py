from typing import Optional
from datetime import datetime
import logging
from src.bitrix.client import BitrixClient
from src.storage import upsert_entity, get_engine
from sqlalchemy.sql import text

logger = logging.getLogger(__name__)

SELECT_FIELDS = [
    "ID","OWNER_ID","OWNER_TYPE_ID","TYPE_ID","PROVIDER_ID","PROVIDER_TYPE_ID","SUBJECT",
    "CREATED","LAST_UPDATED","AUTHOR_ID","RESPONSIBLE_ID","DESCRIPTION"
]

def full_sync(client: BitrixClient, limit: Optional[int] = None) -> int:
    count = 0
    for item in client.list_paginated("crm.activity.list", select=SELECT_FIELDS, order={"ID": "ASC"}, include_total=True):
        upsert_entity("activities", item)
        count += 1
        if limit and count >= limit:
            break
    
    # Update sync_state after full sync
    _update_sync_state(count, is_full=True)
    return count


def incremental_sync(client: BitrixClient, since: Optional[datetime] = None, limit: Optional[int] = None) -> int:
    """
    Sync only activities that were created or modified since last sync.
    Uses LOGIC=OR with >CREATED and >LAST_UPDATED filters to catch both new and updated records.
    """
    if since is None:
        since = _get_last_sync()
    
    if since is None:
        logger.info("No previous sync found, running full sync")
        return full_sync(client, limit)
    
    since_str = since.strftime('%Y-%m-%dT%H:%M:%S')
    logger.info(f"Incremental sync for activities created or modified since {since_str}")
    
    # Activities use CREATED and LAST_UPDATED instead of DATE_CREATE/DATE_MODIFY
    filter_params = {
        "LOGIC": "OR",
        ">CREATED": since_str,
        ">LAST_UPDATED": since_str
    }
    
    count = 0
    for item in client.list_paginated(
        "crm.activity.list",
        select=SELECT_FIELDS,
        order={"ID": "ASC"},
        filter=filter_params,
        include_total=True
    ):
        upsert_entity("activities", item)
        count += 1
        if limit and count >= limit:
            break
    
    _update_sync_state(count, is_full=False)
    logger.info(f"Incremental sync completed: {count} activities")
    return count


def _get_last_sync() -> Optional[datetime]:
    """Get last sync timestamp from sync_state table"""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT last_sync_at FROM bitrix.sync_state WHERE entity = 'activities'")
        )
        row = result.fetchone()
        return row[0] if row else None


def _update_sync_state(count: int, is_full: bool = False):
    """Update sync_state table with new sync timestamp"""
    engine = get_engine()
    with engine.connect() as conn:
        now = datetime.now()
        if is_full:
            conn.execute(
                text("""
                    INSERT INTO bitrix.sync_state (entity, last_sync_at, last_full_sync_at, record_count, status, updated_at)
                    VALUES ('activities', :now, :now, :count, 'completed', :now)
                    ON CONFLICT (entity) DO UPDATE SET
                        last_sync_at = :now,
                        last_full_sync_at = :now,
                        record_count = :count,
                        status = 'completed',
                        updated_at = :now
                """),
                {"now": now, "count": count}
            )
        else:
            conn.execute(
                text("""
                    INSERT INTO bitrix.sync_state (entity, last_sync_at, record_count, status, updated_at)
                    VALUES ('activities', :now, :count, 'completed', :now)
                    ON CONFLICT (entity) DO UPDATE SET
                        last_sync_at = :now,
                        record_count = COALESCE(bitrix.sync_state.record_count, 0) + :count,
                        status = 'completed',
                        updated_at = :now
                """),
                {"now": now, "count": count}
            )
        conn.commit()

