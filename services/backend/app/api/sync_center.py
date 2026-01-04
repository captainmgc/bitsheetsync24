"""
Sync Center API - Birleşik senkronizasyon merkezi
Simplified version for async database operations
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import json

from app.database import get_db

router = APIRouter(prefix="/api/sync-center", tags=["sync-center"])


# ============= Pydantic Models =============

class SyncConfigCreate(BaseModel):
    name: str
    tables: List[str]
    table_views: Optional[Dict[str, int]] = None
    sync_mode: str = "two_way"
    auto_sync: bool = True
    sync_interval: int = 15
    sheet_mode: str = "new"
    sheet_name: Optional[str] = None
    sheet_id: Optional[str] = None


class SyncConfigUpdate(BaseModel):
    name: Optional[str] = None
    auto_sync: Optional[bool] = None
    sync_interval: Optional[int] = None
    status: Optional[str] = None


# ============= API Endpoints =============

@router.get("/configs")
async def list_sync_configs(
    user_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """List all sync configurations"""
    try:
        # Check if table exists
        check_query = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'bitrix' 
                AND table_name = 'sheet_sync_configs'
            )
        """)
        exists_result = await db.execute(check_query)
        table_exists = exists_result.scalar()
        
        if not table_exists:
            return {"configs": [], "message": "No sync configurations found"}
        
        query = text("""
            SELECT id, sheet_id, sheet_url, tables, 
                   sync_interval_minutes, bidirectional,
                   last_sync_at, status, created_at
            FROM bitrix.sheet_sync_configs
            WHERE status != 'deleted'
            ORDER BY created_at DESC
        """)
        
        result = await db.execute(query)
        rows = result.fetchall()
        
        configs = []
        for row in rows:
            tables = json.loads(row[3]) if isinstance(row[3], str) else row[3]
            configs.append({
                "id": row[0],
                "sheet_id": row[1],
                "sheet_url": row[2],
                "tables": tables,
                "sync_interval": row[4],
                "bidirectional": row[5],
                "last_sync": row[6].isoformat() if row[6] else None,
                "status": row[7],
                "created_at": row[8].isoformat() if row[8] else None
            })
        
        return {"configs": configs}
        
    except Exception as e:
        return {"configs": [], "error": str(e)}


@router.get("/configs/{config_id}")
async def get_sync_config(
    config_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific sync configuration"""
    try:
        query = text("""
            SELECT id, sheet_id, sheet_url, tables,
                   sync_interval_minutes, bidirectional,
                   last_sync_at, status, created_at
            FROM bitrix.sheet_sync_configs
            WHERE id = :config_id AND status != 'deleted'
        """)
        
        result = await db.execute(query, {"config_id": config_id})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Sync config not found")
        
        tables = json.loads(row[3]) if isinstance(row[3], str) else row[3]
        
        return {
            "id": row[0],
            "sheet_id": row[1],
            "sheet_url": row[2],
            "tables": tables,
            "sync_interval": row[4],
            "bidirectional": row[5],
            "last_sync": row[6].isoformat() if row[6] else None,
            "status": row[7],
            "created_at": row[8].isoformat() if row[8] else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/configs/{config_id}")
async def delete_sync_config(
    config_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a sync configuration"""
    try:
        query = text("""
            UPDATE bitrix.sheet_sync_configs 
            SET status = 'deleted', updated_at = :now
            WHERE id = :config_id
        """)
        
        await db.execute(query, {
            "config_id": config_id,
            "now": datetime.now()
        })
        await db.commit()
        
        return {"status": "deleted", "config_id": config_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/configs/{config_id}/trigger")
async def trigger_sync(
    config_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger a sync for a configuration"""
    try:
        # Get config
        query = text("""
            SELECT id, sheet_id, tables, bidirectional
            FROM bitrix.sheet_sync_configs
            WHERE id = :config_id AND status = 'active'
        """)
        
        result = await db.execute(query, {"config_id": config_id})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Active sync config not found")
        
        # Update last sync time
        update_query = text("""
            UPDATE bitrix.sheet_sync_configs 
            SET last_sync_at = :now, updated_at = :now
            WHERE id = :config_id
        """)
        
        await db.execute(update_query, {
            "config_id": config_id,
            "now": datetime.now()
        })
        await db.commit()
        
        return {
            "status": "triggered",
            "config_id": config_id,
            "message": "Sync will be processed shortly"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_sync_status(
    db: AsyncSession = Depends(get_db)
):
    """Get overall sync status"""
    try:
        # Count active configs
        count_query = text("""
            SELECT 
                COUNT(*) FILTER (WHERE status = 'active') as active,
                COUNT(*) FILTER (WHERE status = 'paused') as paused,
                COUNT(*) FILTER (WHERE bidirectional = true) as bidirectional
            FROM bitrix.sheet_sync_configs
            WHERE status != 'deleted'
        """)
        
        result = await db.execute(count_query)
        row = result.fetchone()
        
        return {
            "active_configs": row[0] if row else 0,
            "paused_configs": row[1] if row else 0,
            "bidirectional_configs": row[2] if row else 0,
            "status": "operational"
        }
        
    except Exception as e:
        return {
            "active_configs": 0,
            "paused_configs": 0,
            "bidirectional_configs": 0,
            "status": "error",
            "error": str(e)
        }
