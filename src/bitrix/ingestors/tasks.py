from typing import Optional
from datetime import datetime
import logging
from src.bitrix.client import BitrixClient
from src.storage import upsert_entity, get_engine
from sqlalchemy.sql import text

logger = logging.getLogger(__name__)

# All fields needed for tasks sync
SELECT_FIELDS = [
    "ID", "TITLE", "DESCRIPTION", "STATUS", "PRIORITY",
    "RESPONSIBLE_ID", "CREATED_BY", "CHANGED_BY",
    "DEADLINE", "START_DATE_PLAN", "END_DATE_PLAN",
    "CREATED_DATE", "CHANGED_DATE", "CLOSED_DATE",
    "DURATION_PLAN", "DURATION_FACT", "TIME_ESTIMATE", "TIME_SPENT_IN_LOGS",
    "PARENT_ID", "GROUP_ID", "TAGS",
    "ALLOW_CHANGE_DEADLINE", "ALLOW_TIME_TRACKING", "MATCH_WORK_TIME",
    "COMMENTS_COUNT", "NEW_COMMENTS_COUNT"
]

def full_sync(client: BitrixClient, limit: Optional[int] = None) -> int:
    count = 0
    # tasks.task.list returns nested {result:{tasks:[...]}}; client handles it
    # Use select=["*"] to get all fields including STATUS
    for item in client.list_paginated("tasks.task.list", select=["*"], order={"ID": "ASC"}, include_total=True):
        # Normalize lowercase keys to uppercase for consistency
        item = _normalize_task_fields(item)
        
        upsert_entity("tasks", item)
        count += 1
        if limit and count >= limit:
            break
    
    _update_sync_state(count, is_full=True)
    logger.info(f"Full sync completed: {count} tasks")
    return count


def incremental_sync(client: BitrixClient, since: Optional[datetime] = None, limit: Optional[int] = None) -> int:
    """
    Sync only tasks that were created or modified since last sync.
    Uses LOGIC=OR with >CREATED_DATE and >CHANGED_DATE filters.
    """
    if since is None:
        since = _get_last_sync()
    
    if since is None:
        logger.info("No previous sync found, running full sync")
        return full_sync(client, limit)
    
    since_str = since.strftime('%Y-%m-%dT%H:%M:%S')
    logger.info(f"Incremental sync for tasks created or modified since {since_str}")
    
    # Tasks use CREATED_DATE and CHANGED_DATE
    filter_params = {
        "LOGIC": "OR",
        ">CREATED_DATE": since_str,
        ">CHANGED_DATE": since_str
    }
    
    count = 0
    for item in client.list_paginated(
        "tasks.task.list",
        select=["*"],  # Get all fields including STATUS
        order={"ID": "ASC"},
        filter=filter_params,
        include_total=True
    ):
        # Normalize fields
        item = _normalize_task_fields(item)
        
        upsert_entity("tasks", item)
        count += 1
        if limit and count >= limit:
            break
    
    _update_sync_state(count, is_full=False)
    logger.info(f"Incremental sync completed: {count} tasks")
    return count


def _normalize_task_fields(item: dict) -> dict:
    """Normalize task field names from camelCase to UPPERCASE for Bitrix24 tasks API"""
    # Map all camelCase fields to UPPERCASE
    field_mapping = {
        'id': 'ID',
        'title': 'TITLE',
        'description': 'DESCRIPTION',
        'status': 'STATUS',
        'priority': 'PRIORITY',
        'responsibleId': 'RESPONSIBLE_ID',
        'createdBy': 'CREATED_BY',
        'changedBy': 'CHANGED_BY',
        'deadline': 'DEADLINE',
        'startDatePlan': 'START_DATE_PLAN',
        'endDatePlan': 'END_DATE_PLAN',
        'createdDate': 'CREATED_DATE',
        'changedDate': 'CHANGED_DATE',
        'closedDate': 'CLOSED_DATE',
        'durationPlan': 'DURATION_PLAN',
        'durationFact': 'DURATION_FACT',
        'timeEstimate': 'TIME_ESTIMATE',
        'timeSpentInLogs': 'TIME_SPENT_IN_LOGS',
        'parentId': 'PARENT_ID',
        'groupId': 'GROUP_ID',
        'tags': 'TAGS',
        'allowChangeDeadline': 'ALLOW_CHANGE_DEADLINE',
        'allowTimeTracking': 'ALLOW_TIME_TRACKING',
        'matchWorkTime': 'MATCH_WORK_TIME',
        'commentsCount': 'COMMENTS_COUNT',
        'newCommentsCount': 'NEW_COMMENTS_COUNT',
    }
    
    for camel, upper in field_mapping.items():
        if camel in item and upper not in item:
            item[upper] = item[camel]
    
    # Also handle DATE_MODIFY compatibility
    if 'changedDate' in item or 'CHANGED_DATE' in item:
        item['DATE_MODIFY'] = item.get('CHANGED_DATE') or item.get('changedDate')
    
    return item


def _get_last_sync() -> Optional[datetime]:
    """Get last sync timestamp from sync_state table"""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT last_sync_at FROM bitrix.sync_state WHERE entity = 'tasks'")
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
                    VALUES ('tasks', :now, :now, :count, 'completed', :now)
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
                    VALUES ('tasks', :now, :count, 'completed', :now)
                    ON CONFLICT (entity) DO UPDATE SET
                        last_sync_at = :now,
                        record_count = COALESCE(bitrix.sync_state.record_count, 0) + :count,
                        status = 'completed',
                        updated_at = :now
                """),
                {"now": now, "count": count}
            )
        conn.commit()

