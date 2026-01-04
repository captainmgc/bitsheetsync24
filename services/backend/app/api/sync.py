"""
Sync API - Manages synchronization operations
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime
import asyncio
import subprocess
import os
import structlog
import asyncpg

from app.config import settings

router = APIRouter(tags=["sync"])
logger = structlog.get_logger()

# Database pool
_pool: Optional[asyncpg.Pool] = None

async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            min_size=1,
            max_size=5
        )
    return _pool

# Global sync state
sync_state = {
    "is_running": False,
    "last_sync": None,
    "last_result": None,
    "auto_sync_enabled": False,
    "auto_sync_interval": 300,  # 5 minutes default
    "sync_history": []
}

# Background task reference
auto_sync_task: Optional[asyncio.Task] = None


class SyncSettings(BaseModel):
    enabled: bool
    interval: Literal[300, 900, 3600, 86400]  # 5min, 15min, 1hour, daily


class SyncResult(BaseModel):
    success: bool
    started_at: datetime
    finished_at: Optional[datetime] = None
    entities_synced: dict = {}
    error: Optional[str] = None


@router.get("/status")
async def get_sync_status():
    """Get current sync status and history"""
    pool = await get_pool()
    
    # Get last sync times from database
    async with pool.acquire() as conn:
        last_syncs = await conn.fetch("""
            SELECT 
                'deals' as entity,
                MAX(updated_at) as last_sync,
                COUNT(*) as total_count
            FROM bitrix.deals
            UNION ALL
            SELECT 
                'contacts' as entity,
                MAX(updated_at) as last_sync,
                COUNT(*) as total_count
            FROM bitrix.contacts
            UNION ALL
            SELECT 
                'companies' as entity,
                MAX(updated_at) as last_sync,
                COUNT(*) as total_count
            FROM bitrix.companies
            UNION ALL
            SELECT 
                'tasks' as entity,
                MAX(updated_at) as last_sync,
                COUNT(*) as total_count
            FROM bitrix.tasks
            UNION ALL
            SELECT 
                'activities' as entity,
                MAX(updated_at) as last_sync,
                COUNT(*) as total_count
            FROM bitrix.activities
            UNION ALL
            SELECT 
                'task_comments' as entity,
                MAX(updated_at) as last_sync,
                COUNT(*) as total_count
            FROM bitrix.task_comments
            UNION ALL
            SELECT 
                'leads' as entity,
                MAX(updated_at) as last_sync,
                COUNT(*) as total_count
            FROM bitrix.leads
            UNION ALL
            SELECT 
                'users' as entity,
                MAX(updated_at) as last_sync,
                COUNT(*) as total_count
            FROM bitrix.users
            ORDER BY entity
        """)
        
        entities = {row['entity']: {
            "last_sync": row['last_sync'].isoformat() if row['last_sync'] else None,
            "total_count": row['total_count']
        } for row in last_syncs}
    
    # Get sync logs from sync_state table
    async with pool.acquire() as conn:
        sync_logs = await conn.fetch("""
            SELECT entity, last_sync_at, record_count, status, error_message
            FROM bitrix.sync_state
            ORDER BY last_sync_at DESC
            LIMIT 20
        """)
        
        history = [{
            "entity": log['entity'],
            "synced_at": log['last_sync_at'].isoformat() if log['last_sync_at'] else None,
            "records": log['record_count'],
            "status": log['status'],
            "error": log['error_message']
        } for log in sync_logs]
    
    return {
        "is_running": sync_state["is_running"],
        "last_sync": sync_state["last_sync"],
        "auto_sync": {
            "enabled": sync_state["auto_sync_enabled"],
            "interval": sync_state["auto_sync_interval"],
            "interval_label": get_interval_label(sync_state["auto_sync_interval"])
        },
        "entities": entities,
        "history": history
    }


def get_interval_label(seconds: int) -> str:
    """Convert seconds to human readable label"""
    if seconds == 300:
        return "5 dakika"
    elif seconds == 900:
        return "15 dakika"
    elif seconds == 3600:
        return "1 saat"
    elif seconds == 86400:
        return "Günlük"
    return f"{seconds} saniye"


@router.post("/now")
async def sync_now(background_tasks: BackgroundTasks):
    """Trigger immediate sync"""
    if sync_state["is_running"]:
        raise HTTPException(status_code=409, detail="Senkronizasyon zaten çalışıyor")
    
    background_tasks.add_task(run_sync)
    
    return {
        "message": "Senkronizasyon başlatıldı",
        "started_at": datetime.now().isoformat()
    }


async def run_sync():
    """Run the sync process"""
    global sync_state
    
    sync_state["is_running"] = True
    sync_state["last_sync"] = datetime.now().isoformat()
    
    started_at = datetime.now()
    result = {
        "success": False,
        "started_at": started_at.isoformat(),
        "entities_synced": {},
        "error": None
    }
    
    try:
        logger.info("sync_started")
        
        # Run the sync daemon script once
        process = await asyncio.create_subprocess_exec(
            "python3", "-c", """
import sys
sys.path.insert(0, '/opt/bitsheet24')
from src.bitrix.client import BitrixClient
from src.bitrix.ingestors import deals, contacts, companies, activities, tasks, task_comments, leads, users

client = BitrixClient()
results = {}

entities = [
    ('deals', deals),
    ('contacts', contacts),
    ('companies', companies),
    ('activities', activities),
    ('tasks', tasks),
    ('task_comments', task_comments),
    ('leads', leads),
    ('users', users)
]

for name, mod in entities:
    try:
        count = mod.incremental_sync(client)
        results[name] = count
        print(f'{name}:{count}')
    except Exception as e:
        results[name] = -1
        print(f'{name}:ERROR:{e}')
""",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd="/opt/bitsheet24"
        )
        
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=600)
        
        # Parse output
        if stdout:
            for line in stdout.decode().strip().split('\n'):
                if ':' in line:
                    parts = line.split(':')
                    entity = parts[0]
                    if len(parts) == 2 and parts[1].isdigit():
                        result["entities_synced"][entity] = int(parts[1])
                    elif 'ERROR' in line:
                        result["entities_synced"][entity] = -1
        
        result["success"] = process.returncode == 0
        result["finished_at"] = datetime.now().isoformat()
        
        logger.info("sync_completed", entities=result["entities_synced"])
        
    except asyncio.TimeoutError:
        result["error"] = "Senkronizasyon zaman aşımına uğradı (10 dakika)"
        logger.error("sync_timeout")
    except Exception as e:
        result["error"] = str(e)
        logger.error("sync_error", error=str(e))
    finally:
        sync_state["is_running"] = False
        sync_state["last_result"] = result
        
        # Add to history (keep last 50)
        sync_state["sync_history"].insert(0, result)
        sync_state["sync_history"] = sync_state["sync_history"][:50]


@router.post("/auto")
async def set_auto_sync(settings: SyncSettings):
    """Enable/disable automatic sync"""
    global auto_sync_task, sync_state
    
    sync_state["auto_sync_enabled"] = settings.enabled
    sync_state["auto_sync_interval"] = settings.interval
    
    # Cancel existing task if any
    if auto_sync_task and not auto_sync_task.done():
        auto_sync_task.cancel()
        auto_sync_task = None
    
    if settings.enabled:
        # Start new auto sync task
        auto_sync_task = asyncio.create_task(auto_sync_loop(settings.interval))
        logger.info("auto_sync_enabled", interval=settings.interval)
        
        return {
            "message": f"Otomatik senkronizasyon aktif: Her {get_interval_label(settings.interval)}",
            "enabled": True,
            "interval": settings.interval
        }
    else:
        logger.info("auto_sync_disabled")
        return {
            "message": "Otomatik senkronizasyon devre dışı",
            "enabled": False
        }


async def auto_sync_loop(interval: int):
    """Background loop for automatic sync"""
    while sync_state["auto_sync_enabled"]:
        try:
            await asyncio.sleep(interval)
            if sync_state["auto_sync_enabled"] and not sync_state["is_running"]:
                await run_sync()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("auto_sync_error", error=str(e))
            await asyncio.sleep(60)  # Wait a bit before retrying


@router.get("/history")
async def get_sync_history(limit: int = 20):
    """Get sync history"""
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        logs = await conn.fetch("""
            SELECT 
                entity,
                last_sync_at,
                record_count,
                status,
                error_message
            FROM bitrix.sync_state
            ORDER BY last_sync_at DESC
            LIMIT $1
        """, limit)
        
        return [{
            "entity": log['entity'],
            "synced_at": log['last_sync_at'].isoformat() if log['last_sync_at'] else None,
            "records": log['record_count'],
            "status": log['status'],
            "error": log['error_message']
        } for log in logs]


@router.get("/stats")
async def get_sync_stats():
    """Get sync statistics"""
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        # Get entity counts
        counts = await conn.fetch("""
            SELECT 'deals' as entity, COUNT(*) as count FROM bitrix.deals
            UNION ALL SELECT 'contacts', COUNT(*) FROM bitrix.contacts
            UNION ALL SELECT 'companies', COUNT(*) FROM bitrix.companies
            UNION ALL SELECT 'tasks', COUNT(*) FROM bitrix.tasks
            UNION ALL SELECT 'activities', COUNT(*) FROM bitrix.activities
            UNION ALL SELECT 'task_comments', COUNT(*) FROM bitrix.task_comments
            UNION ALL SELECT 'leads', COUNT(*) FROM bitrix.leads
            UNION ALL SELECT 'users', COUNT(*) FROM bitrix.users
        """)
        
        # Get today's sync count
        today_count = await conn.fetchval("""
            SELECT COALESCE(SUM(record_count), 0)
            FROM bitrix.sync_state
            WHERE last_sync_at >= CURRENT_DATE
        """)
        
        return {
            "entities": {row['entity']: row['count'] for row in counts},
            "total_records": sum(row['count'] for row in counts),
            "synced_today": today_count,
            "is_running": sync_state["is_running"],
            "auto_sync_enabled": sync_state["auto_sync_enabled"]
        }
