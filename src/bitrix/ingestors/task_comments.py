from typing import Optional
from datetime import datetime
import logging
from src.bitrix.client import BitrixClient
from src.storage import upsert_entity, get_engine
from sqlalchemy.sql import text

logger = logging.getLogger(__name__)


def full_sync(client: BitrixClient, limit: Optional[int] = None) -> int:
    """
    Sync all task comments by iterating through all tasks.
    This is a heavy operation and should be run once or scheduled weekly.
    """
    count = 0
    
    # Get all task IDs
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT data->>'ID' as task_id FROM bitrix.tasks ORDER BY id"))
        task_ids = [row[0] for row in result.fetchall()]
    
    logger.info(f"Syncing comments for {len(task_ids)} tasks...")
    
    for i, task_id in enumerate(task_ids, 1):
        if i % 100 == 0:
            logger.info(f"Progress: {i}/{len(task_ids)} tasks processed")
        
        try:
            task_count = sync_for_task(client, int(task_id))
            count += task_count
            
            if limit and count >= limit:
                break
                
        except Exception as e:
            logger.error(f"Error syncing comments for task {task_id}: {e}")
            continue
    
    _update_sync_state(count, is_full=True)
    logger.info(f"Full sync completed: {count} comments from {len(task_ids)} tasks")
    return count


def sync_for_task(client: BitrixClient, task_id: int, limit: Optional[int] = None) -> int:
    """Sync comments for a specific task"""
    count = 0
    
    try:
        # task.commentitem.getlist requires TASKID parameter
        response = client.call("task.commentitem.getlist", {"TASKID": task_id})
        
        # Extract result
        if isinstance(response, dict):
            comments = response.get('result', [])
        elif isinstance(response, list):
            comments = response
        else:
            return 0
        
        for item in comments:
            if not isinstance(item, dict):
                continue
                
            # Ensure ID exists
            if not item.get('ID'):
                continue
            
            # Add TASK_ID to item (API response doesn't include it)
            item['TASK_ID'] = str(task_id)
            
            upsert_entity("task_comments", item, task_id=task_id)
            count += 1
            
            if limit and count >= limit:
                break
                
    except Exception as e:
        # API method may not exist or permission denied
        logger.debug(f"Could not fetch comments for task {task_id}: {e}")
        pass
    
    return count


def incremental_sync(client: BitrixClient, since: Optional[datetime] = None, limit: Optional[int] = None) -> int:
    """
    Sync comments for tasks that were modified since last sync.
    More efficient than full sync.
    """
    if since is None:
        since = _get_last_sync()
    
    if since is None:
        logger.info("No previous sync found, running full sync")
        return full_sync(client, limit)
    
    since_str = since.strftime('%Y-%m-%dT%H:%M:%S')
    logger.info(f"Incremental sync for task comments since {since_str}")
    
    # Get tasks modified since last sync
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT data->>'ID' as task_id 
                FROM bitrix.tasks 
                WHERE updated_at > :since 
                ORDER BY id
            """),
            {"since": since}
        )
        task_ids = [row[0] for row in result.fetchall()]
    
    if not task_ids:
        logger.info("No tasks modified since last sync")
        return 0
    
    logger.info(f"Syncing comments for {len(task_ids)} modified tasks...")
    
    count = 0
    for task_id in task_ids:
        try:
            task_count = sync_for_task(client, int(task_id))
            count += task_count
            
            if limit and count >= limit:
                break
                
        except Exception as e:
            logger.error(f"Error syncing comments for task {task_id}: {e}")
            continue
    
    _update_sync_state(count, is_full=False)
    logger.info(f"Incremental sync completed: {count} comments from {len(task_ids)} tasks")
    return count


def _get_last_sync() -> Optional[datetime]:
    """Get last sync timestamp from sync_state table"""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT last_sync_at FROM bitrix.sync_state WHERE entity = 'task_comments'")
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
                    VALUES ('task_comments', :now, :now, :count, 'completed', :now)
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
                    VALUES ('task_comments', :now, :count, 'completed', :now)
                    ON CONFLICT (entity) DO UPDATE SET
                        last_sync_at = :now,
                        record_count = COALESCE(bitrix.sync_state.record_count, 0) + :count,
                        status = 'completed',
                        updated_at = :now
                """),
                {"now": now, "count": count}
            )
        conn.commit()

