from typing import Optional
from datetime import datetime
import logging
from src.bitrix.client import BitrixClient
from src.storage import upsert_entity, get_engine
from sqlalchemy.sql import text

logger = logging.getLogger(__name__)


def full_sync(client: BitrixClient, limit: Optional[int] = None) -> int:
    """Full sync all companies from Bitrix24"""
    count = 0
    
    logger.info("Starting full sync for companies...")
    
    items = client.list_paginated(
        "crm.company.list",
        select=["*", "UF_*"],
        order={"ID": "ASC"}
    )
    
    for item in items:
        if not isinstance(item, dict):
            continue
        
        upsert_entity("companies", item)
        count += 1
        
        if limit and count >= limit:
            break
    
    _update_sync_state(count, is_full=True)
    logger.info(f"Full sync completed: {count} companies")
    return count


def incremental_sync(client: BitrixClient, since: Optional[datetime] = None, limit: Optional[int] = None) -> int:
    """Incremental sync companies modified since last sync"""
    if since is None:
        since = _get_last_sync()
    
    if since is None:
        logger.info("No previous sync found, running full sync")
        return full_sync(client, limit)
    
    since_str = since.strftime('%Y-%m-%dT%H:%M:%S')
    logger.info(f"Incremental sync for companies created or modified since {since_str}")
    
    count = 0
    
    items = client.list_paginated(
        "crm.company.list",
        select=["*", "UF_*"],
        filter={
            "LOGIC": "OR",
            ">DATE_CREATE": since_str,
            ">DATE_MODIFY": since_str
        },
        order={"ID": "ASC"}
    )
    
    for item in items:
        if not isinstance(item, dict):
            continue
        
        upsert_entity("companies", item)
        count += 1
        
        if limit and count >= limit:
            break
    
    _update_sync_state(count, is_full=False)
    logger.info(f"Incremental sync completed: {count} companies")
    return count


def _get_last_sync() -> Optional[datetime]:
    """Get last sync timestamp from sync_state table"""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT last_sync_at FROM bitrix.sync_state WHERE entity = 'companies'")
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
                    VALUES ('companies', :now, :now, :count, 'completed', :now)
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
                    VALUES ('companies', :now, :count, 'completed', :now)
                    ON CONFLICT (entity) DO UPDATE SET
                        last_sync_at = :now,
                        record_count = COALESCE(bitrix.sync_state.record_count, 0) + :count,
                        status = 'completed',
                        updated_at = :now
                """),
                {"now": now, "count": count}
            )
        conn.commit()
