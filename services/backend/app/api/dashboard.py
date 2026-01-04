"""
Dashboard API Endpoints
Provides statistics and overview data for the main dashboard

Handles:
- Summary statistics (deals, contacts, companies counts)
- Sales funnel data
- Recent activities
- Sync status overview
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_, text
from datetime import datetime, timedelta
from collections import defaultdict

from app.database import get_db
from app.models.sheet_sync import SheetSyncConfig, ReverseSyncLog, SheetRowTimestamp
from app.config import settings

import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


# ============================================================================
# SUMMARY STATISTICS
# ============================================================================


@router.get("/stats/summary")
async def get_summary_stats(
    user_id: str = Query(..., description="Kullanıcı ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get summary statistics for the dashboard
    
    Returns counts for deals, contacts, companies, tasks, and activities
    """
    try:
        stats = {}
        
        # Deals count from bitrix schema
        try:
            result = await db.execute(text("SELECT COUNT(*) FROM bitrix.deals"))
            stats['deals'] = {
                'total': result.scalar() or 0,
                'label': 'Anlaşmalar',
                'icon': 'handshake'
            }
        except Exception:
            stats['deals'] = {'total': 0, 'label': 'Anlaşmalar', 'icon': 'handshake'}
        
        # Contacts count
        try:
            result = await db.execute(text("SELECT COUNT(*) FROM bitrix.contacts"))
            stats['contacts'] = {
                'total': result.scalar() or 0,
                'label': 'Kişiler',
                'icon': 'users'
            }
        except Exception:
            stats['contacts'] = {'total': 0, 'label': 'Kişiler', 'icon': 'users'}
        
        # Companies count
        try:
            result = await db.execute(text("SELECT COUNT(*) FROM bitrix.companies"))
            stats['companies'] = {
                'total': result.scalar() or 0,
                'label': 'Şirketler',
                'icon': 'building'
            }
        except Exception:
            stats['companies'] = {'total': 0, 'label': 'Şirketler', 'icon': 'building'}
        
        # Tasks count
        try:
            result = await db.execute(text("SELECT COUNT(*) FROM bitrix.tasks"))
            stats['tasks'] = {
                'total': result.scalar() or 0,
                'label': 'Görevler',
                'icon': 'clipboard-list'
            }
        except Exception:
            stats['tasks'] = {'total': 0, 'label': 'Görevler', 'icon': 'clipboard-list'}
        
        # Activities count
        try:
            result = await db.execute(text("SELECT COUNT(*) FROM bitrix.activities"))
            stats['activities'] = {
                'total': result.scalar() or 0,
                'label': 'Aktiviteler',
                'icon': 'activity'
            }
        except Exception:
            stats['activities'] = {'total': 0, 'label': 'Aktiviteler', 'icon': 'activity'}
        
        # Sync configs count
        try:
            configs_result = await db.execute(
                select(func.count(SheetSyncConfig.id)).where(
                    SheetSyncConfig.user_id == user_id
                )
            )
            stats['sync_configs'] = {
                'total': configs_result.scalar() or 0,
                'label': 'Senkronizasyon',
                'icon': 'refresh-cw'
            }
        except Exception:
            stats['sync_configs'] = {'total': 0, 'label': 'Senkronizasyon', 'icon': 'refresh-cw'}
        
        return {
            'success': True,
            'stats': stats,
            'generated_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("get_summary_stats_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/stats/deals-by-stage")
async def get_deals_by_stage(
    user_id: str = Query(..., description="Kullanıcı ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get deals grouped by stage for sales funnel visualization
    """
    try:
        # Get deals with stage information from bitrix schema
        result = await db.execute(text("""
            SELECT 
                COALESCE(stage_id, 'UNKNOWN') as stage_id,
                COUNT(*) as count,
                COALESCE(SUM(COALESCE(opportunity, 0)), 0) as amount
            FROM bitrix.deals
            GROUP BY stage_id
            ORDER BY count DESC
        """))
        rows = result.fetchall()
        
        # Map stage_id to human readable name
        stage_mapping = {
            'NEW': 'Yeni',
            'PREPARATION': 'Hazırlık',
            'PREPAYMENT_INVOICE': 'Ön Ödeme Faturası',
            'EXECUTING': 'Yürütme',
            'FINAL_INVOICE': 'Son Fatura',
            'WON': 'Kazanıldı',
            'LOSE': 'Kaybedildi',
            'APOLOGY': 'İptal',
            'C1:NEW': 'Yeni',
            'C1:PREPARATION': 'Hazırlık',
            'C1:EXECUTING': 'Yürütme',
            'C1:FINAL_INVOICE': 'Son Fatura',
            'C1:WON': 'Kazanıldı',
            'C1:LOSE': 'Kaybedildi',
            'UNKNOWN': 'Bilinmeyen',
        }
        
        # First pass: calculate totals
        stages_data = []
        total_deals = 0
        total_amount = 0
        
        for row in rows:
            stage_id = str(row[0]) if row[0] else 'UNKNOWN'
            count = row[1] or 0
            amount = float(row[2]) if row[2] else 0
            
            stage_name = stage_mapping.get(stage_id, stage_id)
            
            stages_data.append({
                'stage_id': stage_id,
                'stage_name': stage_name,
                'count': count,
                'total_amount': amount
            })
            total_deals += count
            total_amount += amount
        
        # Second pass: calculate percentages
        stages = []
        for stage in stages_data:
            percentage = (stage['count'] / total_deals * 100) if total_deals > 0 else 0
            stages.append({
                'stage_id': stage['stage_id'],
                'stage_name': stage['stage_name'],
                'count': stage['count'],
                'total_amount': stage['total_amount'],
                'percentage': round(percentage, 2)
            })
        
        return {
            'stages': stages,
            'total_deals': total_deals,
            'total_amount': total_amount
        }
        
    except Exception as e:
        logger.error("get_deals_by_stage_error", error=str(e))
        # Return empty data on error
        return {
            'stages': [],
            'total_deals': 0,
            'total_amount': 0
        }


@router.get("/activities/recent")
async def get_recent_activities(
    user_id: str = Query(..., description="Kullanıcı ID"),
    limit: int = Query(20, ge=1, le=100, description="Kayıt limiti"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get recent sync and system activities
    """
    try:
        activities = []
        
        # Get recent sync logs
        try:
            stmt = select(ReverseSyncLog).order_by(
                desc(ReverseSyncLog.created_at)
            ).limit(limit)
            result = await db.execute(stmt)
            sync_logs = list(result.scalars().all())
            
            for log in sync_logs:
                activities.append({
                    'id': f"sync-{log.id}",
                    'type': 'sync',
                    'status': log.status,
                    'description': f"Satır {log.row_number or '-'} senkronize edildi" if log.status == 'completed' else f"Satır {log.row_number or '-'} senkronizasyonu {'başarısız' if log.status == 'failed' else 'bekliyor'}",
                    'entity_id': log.entity_id,
                    'row_number': log.row_number,
                    'error': log.error_message,
                    'created_at': log.created_at.isoformat() if log.created_at else None,
                    'icon': 'refresh-cw' if log.status == 'completed' else 'alert-circle' if log.status == 'failed' else 'clock'
                })
        except Exception as e:
            logger.warning("get_sync_logs_warning", error=str(e))
        
        # Get recent sync config updates
        try:
            stmt = select(SheetSyncConfig).where(
                SheetSyncConfig.user_id == user_id
            ).order_by(desc(SheetSyncConfig.last_sync_at)).limit(10)
            result = await db.execute(stmt)
            configs = list(result.scalars().all())
            
            for config in configs:
                if config.last_sync_at:
                    activities.append({
                        'id': f"config-{config.id}",
                        'type': 'config_sync',
                        'status': 'completed',
                        'description': f"{config.sheet_name} sayfası senkronize edildi",
                        'entity_type': config.entity_type,
                        'config_id': config.id,
                        'created_at': config.last_sync_at.isoformat() if config.last_sync_at else None,
                        'icon': 'file-spreadsheet'
                    })
        except Exception as e:
            logger.warning("get_config_activities_warning", error=str(e))
        
        # Sort by created_at
        activities.sort(key=lambda x: x.get('created_at') or '', reverse=True)
        
        return {
            'success': True,
            'activities': activities[:limit],
            'total': len(activities),
            'generated_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("get_recent_activities_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/sync/status")
async def get_sync_status(
    user_id: str = Query(..., description="Kullanıcı ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get overall sync status for all configurations
    """
    try:
        # Get all sync configs for user
        stmt = select(SheetSyncConfig).where(
            SheetSyncConfig.user_id == user_id
        )
        result = await db.execute(stmt)
        configs = list(result.scalars().all())
        
        sync_status = {
            'total_configs': len(configs),
            'active_configs': 0,
            'configs_with_errors': 0,
            'last_sync': None,
            'errors_last_24h': 0,
            'success_rate': 100.0,
            'overall_status': 'healthy',
            'configs': []
        }
        
        for config in configs:
            config_status = {
                'id': config.id,
                'name': config.sheet_name,
                'sheet_name': config.sheet_name,
                'entity_type': config.entity_type,
                'enabled': config.enabled,
                'last_sync': config.last_sync_at.isoformat() if config.last_sync_at else None,
                'last_sync_at': config.last_sync_at.isoformat() if config.last_sync_at else None,
                'direction': 'bidirectional',
                'status': 'active' if config.enabled else 'disabled',
                'has_error': False,
                'error_count': 0
            }
            
            if config.enabled:
                sync_status['active_configs'] += 1
            
            # Check for recent errors
            try:
                error_stmt = select(func.count(ReverseSyncLog.id)).where(
                    and_(
                        ReverseSyncLog.config_id == config.id,
                        ReverseSyncLog.status == 'failed',
                        ReverseSyncLog.created_at >= datetime.utcnow() - timedelta(hours=24)
                    )
                )
                error_result = await db.execute(error_stmt)
                error_count = error_result.scalar() or 0
                
                if error_count > 0:
                    config_status['has_error'] = True
                    config_status['error_count'] = error_count
                    sync_status['configs_with_errors'] += 1
                    sync_status['errors_last_24h'] += error_count
            except Exception:
                pass
            
            # Update last sync time
            if config.last_sync_at:
                if sync_status['last_sync'] is None or config.last_sync_at > datetime.fromisoformat(sync_status['last_sync'].replace('Z', '+00:00')):
                    sync_status['last_sync'] = config.last_sync_at.isoformat()
            
            sync_status['configs'].append(config_status)
        
        # Calculate success rate from last 24h
        try:
            total_stmt = select(func.count(ReverseSyncLog.id)).where(
                ReverseSyncLog.created_at >= datetime.utcnow() - timedelta(hours=24)
            )
            total_result = await db.execute(total_stmt)
            total_syncs = total_result.scalar() or 0
            
            if total_syncs > 0:
                success_stmt = select(func.count(ReverseSyncLog.id)).where(
                    and_(
                        ReverseSyncLog.status == 'success',
                        ReverseSyncLog.created_at >= datetime.utcnow() - timedelta(hours=24)
                    )
                )
                success_result = await db.execute(success_stmt)
                success_count = success_result.scalar() or 0
                sync_status['success_rate'] = round((success_count / total_syncs) * 100, 1)
        except Exception:
            pass
        
        # Calculate overall health and status
        if sync_status['total_configs'] == 0:
            sync_status['health'] = 'no_config'
            sync_status['health_label'] = 'Yapılandırma Yok'
            sync_status['overall_status'] = 'no_config'
        elif sync_status['configs_with_errors'] > 0:
            sync_status['health'] = 'warning'
            sync_status['health_label'] = 'Hatalar Mevcut'
            sync_status['overall_status'] = 'warning'
        elif sync_status['active_configs'] == 0:
            sync_status['health'] = 'inactive'
            sync_status['health_label'] = 'Pasif'
            sync_status['overall_status'] = 'inactive'
        else:
            sync_status['health'] = 'healthy'
            sync_status['health_label'] = 'Sağlıklı'
            sync_status['overall_status'] = 'healthy'
        
        # Return sync_status directly (not nested)
        return sync_status
        
    except Exception as e:
        logger.error("get_sync_status_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/stats/trends")
async def get_trends(
    user_id: str = Query(..., description="Kullanıcı ID"),
    days: int = Query(7, ge=1, le=30, description="Gün sayısı"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get sync activity trends over time
    """
    try:
        trends = []
        now = datetime.utcnow()
        
        for i in range(days - 1, -1, -1):
            day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            # Count syncs for this day
            try:
                stmt = select(func.count(ReverseSyncLog.id)).where(
                    and_(
                        ReverseSyncLog.created_at >= day_start,
                        ReverseSyncLog.created_at < day_end
                    )
                )
                result = await db.execute(stmt)
                sync_count = result.scalar() or 0
                
                # Count successful syncs
                success_stmt = select(func.count(ReverseSyncLog.id)).where(
                    and_(
                        ReverseSyncLog.created_at >= day_start,
                        ReverseSyncLog.created_at < day_end,
                        ReverseSyncLog.status == 'completed'
                    )
                )
                success_result = await db.execute(success_stmt)
                success_count = success_result.scalar() or 0
                
                trends.append({
                    'date': day_start.strftime('%Y-%m-%d'),
                    'day_name': day_start.strftime('%A'),
                    'total': sync_count,
                    'successful': success_count,
                    'failed': sync_count - success_count
                })
            except Exception:
                trends.append({
                    'date': day_start.strftime('%Y-%m-%d'),
                    'day_name': day_start.strftime('%A'),
                    'total': 0,
                    'successful': 0,
                    'failed': 0
                })
        
        return {
            'success': True,
            'trends': trends,
            'period_days': days,
            'generated_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("get_trends_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
