from typing import Optional
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.bitrix.client import BitrixClient
from src.storage import upsert_entity, get_engine
from sqlalchemy.sql import text

logger = logging.getLogger(__name__)


def full_sync(client: BitrixClient, limit: Optional[int] = None, batch_size: int = 5, max_workers: int = 2) -> int:
    """
    Sync all task comments by iterating through all tasks.
    This is a heavy operation and should be run once or scheduled weekly.
    
    RESUME CAPABILITY: Only processes tasks that haven't been synced yet
    PARALLEL PROCESSING: Process multiple tasks concurrently
    
    Args:
        client: Bitrix API client
        limit: Maximum number of comments to sync (None = all)
        batch_size: Number of tasks to process in each batch
        max_workers: Maximum number of parallel workers
    """
    count = 0
    
    # Get task IDs that haven't been synced yet (not in task_comments table)
    # Support both normalized (bitrix_id) and legacy (data->>'ID') tables
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT t.bitrix_id as task_id 
            FROM bitrix.tasks t
            WHERE t.bitrix_id IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM bitrix.task_comments tc 
                WHERE tc.task_id::text = t.bitrix_id
            )
            ORDER BY t.id
        """))
        task_ids = [row[0] for row in result.fetchall()]
    
    total_tasks = 43431
    synced_tasks = total_tasks - len(task_ids)
    
    logger.info(f"Resuming sync: {synced_tasks}/{total_tasks} tasks already synced")
    logger.info(f"Remaining: {len(task_ids)} tasks to process")
    logger.info(f"Using {max_workers} parallel workers with batch size {batch_size}")
    
    # Process in batches with parallel workers
    for batch_start in range(0, len(task_ids), batch_size):
        batch_end = min(batch_start + batch_size, len(task_ids))
        batch = task_ids[batch_start:batch_end]
        
        # Process batch in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks in batch
            future_to_task = {
                executor.submit(sync_for_task, client, int(task_id), timeout=5): task_id 
                for task_id in batch
            }
            
            # Collect results
            for future in as_completed(future_to_task):
                task_id = future_to_task[future]
                try:
                    task_count = future.result()
                    count += task_count
                except Exception as e:
                    logger.error(f"Error syncing task {task_id}: {e}")
        
        # Progress update
        processed = synced_tasks + batch_end
        percentage = (processed / total_tasks) * 100
        remaining = len(task_ids) - batch_end
        logger.info(f"Progress: {processed}/{total_tasks} ({percentage:.1f}%) - {count} comments - {remaining} tasks remaining")
        
        if limit and count >= limit:
            break
    
    _update_sync_state(count, is_full=True)
    logger.info(f"Full sync completed: {count} new comments from {len(task_ids)} tasks")
    logger.info(f"Total synced: {synced_tasks + len(task_ids)}/{total_tasks} tasks")
    return count


def sync_for_task(client: BitrixClient, task_id: int, limit: Optional[int] = None, timeout: int = 15) -> int:
    """Sync comments for a specific task with timeout"""
    import httpx
    import time
    count = 0
    
    try:
        # Add delay to avoid rate limiting
        time.sleep(0.5)
        
        # Set shorter timeout for this call
        old_timeout = client._client.timeout
        client._client.timeout = httpx.Timeout(timeout)
        
        # task.commentitem.getlist requires TASKID parameter
        response = client.call("task.commentitem.getlist", {"TASKID": task_id})
        
        # Restore original timeout
        client._client.timeout = old_timeout
        
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
                
    except (httpx.TimeoutException, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
        logger.warning(f"Timeout for task {task_id} - skipping")
        return 0
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
    
    # Get tasks modified since last sync (support normalized table with bitrix_id)
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT bitrix_id as task_id 
                FROM bitrix.tasks 
                WHERE bitrix_id IS NOT NULL
                AND updated_at > :since 
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

