"""
Error Logs API
Provides endpoints for viewing and managing sync errors
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from datetime import datetime, timedelta
import structlog

from app.database import get_db

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/errors", tags=["errors"])


class ErrorLog(BaseModel):
    id: int
    error_type: str
    severity: str
    source: str
    message: str
    stack_trace: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    created_at: str
    resolved: bool
    resolved_at: Optional[str] = None
    retry_count: int
    max_retries: int


class ErrorStats(BaseModel):
    total_errors: int
    unresolved_errors: int
    critical_errors: int
    today_errors: int
    error_rate: float


class ErrorListResponse(BaseModel):
    errors: List[ErrorLog]
    total: int
    page: int
    page_size: int
    total_pages: int


def classify_severity(error_message: str) -> str:
    """Classify error severity based on message"""
    msg_lower = error_message.lower() if error_message else ""
    
    # Critical: Authentication, permission errors
    if any(x in msg_lower for x in ['authentication', 'permission', 'unauthorized', 'forbidden', 'critical']):
        return 'critical'
    
    # High: Connection errors, timeouts
    if any(x in msg_lower for x in ['timeout', 'connection', 'network', 'unreachable', 'fail']):
        return 'high'
    
    # Medium: Validation, format errors
    if any(x in msg_lower for x in ['validation', 'format', 'invalid', 'parse']):
        return 'medium'
    
    # Low: Everything else
    return 'low'


def classify_error_type(error_message: str, source: str) -> str:
    """Classify error type based on message and source"""
    msg_lower = error_message.lower() if error_message else ""
    
    if 'api' in msg_lower or 'bitrix' in source.lower():
        return 'API_ERROR'
    if 'validation' in msg_lower or 'invalid' in msg_lower:
        return 'VALIDATION_ERROR'
    if 'connection' in msg_lower or 'timeout' in msg_lower:
        return 'CONNECTION_ERROR'
    if 'database' in msg_lower or 'sql' in msg_lower:
        return 'DATABASE_ERROR'
    if 'sheet' in msg_lower or 'google' in msg_lower:
        return 'SHEETS_ERROR'
    
    return 'SYNC_ERROR'


@router.get("/", response_model=ErrorListResponse)
async def get_errors(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    severity: Optional[str] = Query(default=None, description="Filter by severity: low, medium, high, critical"),
    resolved: Optional[bool] = Query(default=None, description="Filter by resolved status"),
    source: Optional[str] = Query(default=None, description="Filter by source"),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated list of sync errors"""
    try:
        # Build query
        where_clauses = ["status = 'failed'"]
        params = {}
        
        if resolved is not None:
            if resolved:
                where_clauses.append("synced_at IS NOT NULL")
            else:
                where_clauses.append("synced_at IS NULL")
        
        where_sql = " AND ".join(where_clauses)
        
        # Count total
        count_query = text(f"""
            SELECT COUNT(*) as total
            FROM reverse_sync_logs
            WHERE {where_sql}
        """)
        count_result = await db.execute(count_query, params)
        total = count_result.scalar() or 0
        
        # Get errors - using only existing columns
        offset = (page - 1) * page_size
        data_query = text(f"""
            SELECT 
                id,
                config_id,
                user_id,
                entity_id,
                sheet_row_id,
                changed_fields,
                status,
                error_message,
                webhook_payload,
                synced_at,
                created_at
            FROM reverse_sync_logs
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        
        result = await db.execute(data_query, {"limit": page_size, "offset": offset, **params})
        rows = result.fetchall()
        
        errors = []
        for row in rows:
            error_msg = row.error_message or "Bilinmeyen hata"
            
            # Determine source
            source_name = f"sync_config_{row.config_id}" if row.config_id else "reverse_sync"
            
            # Classify error
            error_type = classify_error_type(error_msg, source_name)
            severity_level = classify_severity(error_msg)
            
            # Filter by severity if specified
            if severity and severity_level != severity:
                continue
            
            # Parse stack trace from webhook_payload or changed_fields
            stack_trace = None
            if row.webhook_payload:
                try:
                    if isinstance(row.webhook_payload, dict):
                        stack_trace = row.webhook_payload.get('traceback') or row.webhook_payload.get('stack_trace')
                except:
                    pass
            
            errors.append(ErrorLog(
                id=row.id,
                error_type=error_type,
                severity=severity_level,
                source=source_name,
                message=error_msg,
                stack_trace=stack_trace,
                entity_type="deal",  # Default entity type
                entity_id=str(row.entity_id) if row.entity_id else None,
                created_at=row.created_at.isoformat() if row.created_at else "",
                resolved=row.synced_at is not None,
                resolved_at=row.synced_at.isoformat() if row.synced_at else None,
                retry_count=0,  # Not tracked in this table
                max_retries=3   # Default
            ))
        
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        
        return ErrorListResponse(
            errors=errors,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
    except Exception as e:
        logger.error("get_errors_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Hatalar alınırken hata: {str(e)}")


@router.get("/stats", response_model=ErrorStats)
async def get_error_stats(
    db: AsyncSession = Depends(get_db)
):
    """Get error statistics summary"""
    try:
        # Get stats from reverse_sync_logs - using only existing columns
        stats_query = text("""
            SELECT 
                COUNT(*) as total_errors,
                COUNT(CASE WHEN synced_at IS NULL AND status = 'failed' THEN 1 END) as unresolved_errors,
                COUNT(CASE WHEN created_at >= NOW() - INTERVAL '24 hours' AND status = 'failed' THEN 1 END) as today_errors,
                COUNT(CASE WHEN created_at >= NOW() - INTERVAL '7 days' THEN 1 END) as week_total,
                COUNT(CASE WHEN created_at >= NOW() - INTERVAL '7 days' AND status = 'failed' THEN 1 END) as week_errors
            FROM reverse_sync_logs
            WHERE status = 'failed'
        """)
        
        result = await db.execute(stats_query)
        row = result.fetchone()
        
        if row:
            week_total = row.week_total or 1
            week_errors = row.week_errors or 0
            error_rate = round((week_errors / week_total) * 100, 1) if week_total > 0 else 0
            
            # Critical errors = unresolved errors (no retry tracking available)
            critical_errors = row.unresolved_errors or 0
            
            return ErrorStats(
                total_errors=row.total_errors or 0,
                unresolved_errors=row.unresolved_errors or 0,
                critical_errors=critical_errors,
                today_errors=row.today_errors or 0,
                error_rate=error_rate
            )
        
        return ErrorStats(
            total_errors=0,
            unresolved_errors=0,
            critical_errors=0,
            today_errors=0,
            error_rate=0.0
        )
        
    except Exception as e:
        logger.error("get_error_stats_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"İstatistikler alınırken hata: {str(e)}")


@router.post("/{error_id}/resolve")
async def resolve_error(
    error_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Mark an error as resolved"""
    try:
        update_query = text("""
            UPDATE reverse_sync_logs 
            SET synced_at = NOW(), status = 'resolved'
            WHERE id = :error_id
            RETURNING id
        """)
        
        result = await db.execute(update_query, {"error_id": error_id})
        await db.commit()
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Hata kaydı bulunamadı")
        
        return {"message": "Hata çözüldü olarak işaretlendi", "id": error_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("resolve_error_failed", error_id=error_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Hata işaretlenirken hata: {str(e)}")


@router.post("/{error_id}/retry")
async def retry_error(
    error_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Retry a failed sync operation"""
    try:
        # Get error details
        query = text("""
            SELECT id, config_id, entity_id, status
            FROM reverse_sync_logs
            WHERE id = :error_id AND status = 'failed'
        """)
        
        result = await db.execute(query, {"error_id": error_id})
        error = result.fetchone()
        
        if not error:
            raise HTTPException(status_code=404, detail="Hata kaydı bulunamadı veya zaten çözüldü")
        
        # Set status to pending for retry
        update_query = text("""
            UPDATE reverse_sync_logs 
            SET status = 'pending'
            WHERE id = :error_id
            RETURNING id
        """)
        
        result = await db.execute(update_query, {"error_id": error_id})
        await db.commit()
        
        return {
            "message": "Yeniden deneme kuyruğa alındı",
            "id": error_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("retry_error_failed", error_id=error_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Yeniden deneme başlatılırken hata: {str(e)}")


@router.delete("/{error_id}")
async def delete_error(
    error_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete an error log"""
    try:
        delete_query = text("""
            DELETE FROM reverse_sync_logs
            WHERE id = :error_id
            RETURNING id
        """)
        
        result = await db.execute(delete_query, {"error_id": error_id})
        await db.commit()
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Hata kaydı bulunamadı")
        
        return {"message": "Hata kaydı silindi", "id": error_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_error_failed", error_id=error_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Hata silinirken hata: {str(e)}")


@router.post("/resolve-all")
async def resolve_all_errors(
    severity: Optional[str] = Query(default=None, description="Only resolve errors of this severity"),
    db: AsyncSession = Depends(get_db)
):
    """Mark all errors as resolved"""
    try:
        update_query = text("""
            UPDATE reverse_sync_logs 
            SET synced_at = NOW(), status = 'resolved'
            WHERE status = 'failed' AND synced_at IS NULL
            RETURNING id
        """)
        
        result = await db.execute(update_query)
        await db.commit()
        
        count = result.rowcount
        
        return {"message": f"{count} hata çözüldü olarak işaretlendi", "resolved_count": count}
        
    except Exception as e:
        logger.error("resolve_all_errors_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Hatalar işaretlenirken hata: {str(e)}")
