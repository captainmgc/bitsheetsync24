from typing import Optional
from datetime import datetime
import logging
from bitrix.client import BitrixClient
from storage import upsert_entity, get_engine
from sqlalchemy.sql import text

logger = logging.getLogger(__name__)

def full_sync(client: BitrixClient, limit: Optional[int] = None) -> int:
    """Sync all users from Bitrix24"""
    count = 0
    
    # Bitrix24 user.get tüm kullanıcıları bir seferde döndürür
    response = client.call("user.get", {"ACTIVE": True})
    
    # Extract result from response
    if isinstance(response, dict):
        result = response.get('result', [])
    elif isinstance(response, list):
        result = response
    else:
        logger.warning(f"Unexpected response format: {type(response)}")
        return 0
    
    if not result:
        logger.warning("No users in result")
        return 0
    
    for item in result:
        if not isinstance(item, dict) or not item.get('ID'):
            continue
            
        upsert_entity("users", item)
        count += 1
        
        if limit and count >= limit:
            break
    
    _update_sync_state(count, is_full=True)
    logger.info(f"Full sync completed: {count} users")
    return count


def _get_last_sync() -> Optional[datetime]:
    """Get last sync timestamp from sync_state table"""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT last_sync_at FROM bitrix.sync_state WHERE entity = 'users'")
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
                    VALUES ('users', :now, :now, :count, 'completed', :now)
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
                    VALUES ('users', :now, :count, 'completed', :now)
                    ON CONFLICT (entity) DO UPDATE SET
                        last_sync_at = :now,
                        record_count = COALESCE(bitrix.sync_state.record_count, 0) + :count,
                        status = 'completed',
                        updated_at = :now
                """),
                {"now": now, "count": count}
            )
        conn.commit()
