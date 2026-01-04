"""
Bidirectional Sync API - Google Sheets ↔ Bitrix24
Enables:
- Incremental updates from Bitrix24 to Google Sheets
- Change detection from Google Sheets
- Updates from Google Sheets to Bitrix24
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import structlog
import json
import os

from app.database import get_db
from app.schemas.sheets import (
    SheetSyncConfigCreate,
    SheetSyncConfigResponse,
    SyncChangesRequest,
    SyncChangesResponse
)
from app.services.google_sheets_api import GoogleSheetsService

router = APIRouter(prefix="/api/v1/bidirectional-sync", tags=["Bidirectional Sync"])
logger = structlog.get_logger()

# Bitrix24 API mapping
ENTITY_API_MAP = {
    'contacts': {'method': 'crm.contact.update', 'id_field': 'ID'},
    'companies': {'method': 'crm.company.update', 'id_field': 'ID'},
    'deals': {'method': 'crm.deal.update', 'id_field': 'ID'},
    'leads': {'method': 'crm.lead.update', 'id_field': 'ID'},
    'activities': {'method': 'crm.activity.update', 'id_field': 'ID'},
    'tasks': {'method': 'tasks.task.update', 'id_field': 'id'},
}


@router.post("/configs", response_model=SheetSyncConfigResponse)
async def create_sync_config(
    config: SheetSyncConfigCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new bidirectional sync configuration
    """
    try:
        # Store sync configuration
        query = text("""
            INSERT INTO bitrix.sheet_sync_configs (
                sheet_id,
                sheet_url,
                tables,
                access_token,
                refresh_token,
                sync_interval_minutes,
                bidirectional,
                status,
                created_at
            ) VALUES (
                :sheet_id,
                :sheet_url,
                :tables,
                :access_token,
                :refresh_token,
                :sync_interval_minutes,
                :bidirectional,
                'active',
                :created_at
            )
            RETURNING id, created_at
        """)
        
        result = await db.execute(query, {
            "sheet_id": config.sheet_id,
            "sheet_url": config.sheet_url,
            "tables": json.dumps(config.tables),
            "access_token": config.access_token,
            "refresh_token": config.refresh_token,
            "sync_interval_minutes": config.sync_interval_minutes,
            "bidirectional": config.bidirectional,
            "created_at": datetime.now()
        })
        
        row = result.fetchone()
        await db.commit()
        
        # Store initial data snapshot for change detection
        await _store_initial_snapshot(db, row[0], config)
        
        logger.info("sync_config_created", config_id=row[0], tables=config.tables)
        
        return SheetSyncConfigResponse(
            id=row[0],
            sheet_id=config.sheet_id,
            sheet_url=config.sheet_url,
            tables=config.tables,
            sync_interval_minutes=config.sync_interval_minutes,
            bidirectional=config.bidirectional,
            status="active",
            created_at=row[1],
            next_sync_at=datetime.now() + timedelta(minutes=config.sync_interval_minutes)
        )
        
    except Exception as e:
        logger.error("create_sync_config_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/configs", response_model=List[SheetSyncConfigResponse])
async def list_sync_configs(
    db: AsyncSession = Depends(get_db)
):
    """
    List all sync configurations
    """
    try:
        query = text("""
            SELECT 
                id, sheet_id, sheet_url, tables, 
                sync_interval_minutes, bidirectional,
                last_sync_at, status, created_at, updated_at
            FROM bitrix.sheet_sync_configs
            WHERE status != 'deleted'
            ORDER BY created_at DESC
        """)
        
        result = await db.execute(query)
        rows = result.fetchall()
        
        configs = []
        for row in rows:
            tables = json.loads(row[3]) if isinstance(row[3], str) else row[3]
            next_sync = None
            if row[6]:  # last_sync_at
                next_sync = row[6] + timedelta(minutes=row[4])
            
            configs.append(SheetSyncConfigResponse(
                id=row[0],
                sheet_id=row[1],
                sheet_url=row[2],
                tables=tables,
                sync_interval_minutes=row[4],
                bidirectional=row[5],
                last_sync_at=row[6],
                next_sync_at=next_sync,
                status=row[7],
                created_at=row[8],
                updated_at=row[9]
            ))
        
        return configs
        
    except Exception as e:
        logger.error("list_sync_configs_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/configs/{config_id}/sync-to-sheet")
async def sync_to_sheet(
    config_id: int,
    access_token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Sync incremental changes from Bitrix24 (local DB) to Google Sheets
    """
    try:
        # Get config
        config = await _get_sync_config(db, config_id)
        if not config:
            raise HTTPException(status_code=404, detail="Sync config not found")
        
        sheets_service = GoogleSheetsService(access_token)
        tables = json.loads(config['tables']) if isinstance(config['tables'], str) else config['tables']
        
        total_updated = 0
        results = []
        
        for table_name in tables:
            # Get changes since last sync
            last_sync = config['last_sync_at'] or datetime(2020, 1, 1)
            
            changes_query = text(f"""
                SELECT * FROM bitrix.{table_name}
                WHERE updated_at > :last_sync OR created_at > :last_sync
                ORDER BY id
            """)
            
            result = await db.execute(changes_query, {"last_sync": last_sync})
            rows = result.mappings().all()
            
            if not rows:
                continue
            
            # Get current sheet data to find row positions
            sheet_data = await sheets_service.get_values(
                config['sheet_id'],
                f"{table_name}!A:A"
            )
            
            existing_ids = set()
            if sheet_data.get('values'):
                # Skip header, get IDs
                for i, row in enumerate(sheet_data['values'][1:], start=2):
                    if row:
                        existing_ids.add(str(row[0]))
            
            # Prepare updates
            headers = list(rows[0].keys())
            new_rows = []
            
            for row in rows:
                row_id = str(row.get('id', ''))
                row_data = [str(row.get(col, '') or '') for col in headers]
                
                if row_id not in existing_ids:
                    new_rows.append(row_data)
            
            # Append new rows
            if new_rows:
                await sheets_service.append_values(
                    config['sheet_id'],
                    f"{table_name}!A1",
                    new_rows
                )
                total_updated += len(new_rows)
            
            results.append({
                "table": table_name,
                "new_rows": len(new_rows),
                "total_changes": len(rows)
            })
        
        # Update last sync time
        await db.execute(
            text("UPDATE bitrix.sheet_sync_configs SET last_sync_at = :now, updated_at = :now WHERE id = :id"),
            {"now": datetime.now(), "id": config_id}
        )
        await db.commit()
        
        await sheets_service.close()
        
        return {
            "status": "success",
            "config_id": config_id,
            "total_updated": total_updated,
            "details": results
        }
        
    except Exception as e:
        logger.error("sync_to_sheet_error", error=str(e), config_id=config_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/configs/{config_id}/sync-from-sheet", response_model=SyncChangesResponse)
async def sync_from_sheet(
    config_id: int,
    request: SyncChangesRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Detect and sync changes from Google Sheets to Bitrix24
    """
    try:
        config = await _get_sync_config(db, config_id)
        if not config:
            raise HTTPException(status_code=404, detail="Sync config not found")
        
        if not config['bidirectional']:
            raise HTTPException(status_code=400, detail="Bidirectional sync not enabled for this config")
        
        sheets_service = GoogleSheetsService(request.access_token)
        tables = json.loads(config['tables']) if isinstance(config['tables'], str) else config['tables']
        
        changes_detected = 0
        changes_synced = 0
        errors = []
        details = []
        
        for table_name in tables:
            try:
                # Read all data from sheet
                sheet_data = await sheets_service.get_values(
                    config['sheet_id'],
                    f"{table_name}!A1:ZZ"
                )
                
                if not sheet_data.get('values') or len(sheet_data['values']) < 2:
                    continue
                
                headers = sheet_data['values'][0]
                rows = sheet_data['values'][1:]
                
                # Get snapshot for comparison
                snapshot = await _get_snapshot(db, config_id, table_name)
                
                # Detect changes
                table_changes = []
                for row_idx, row in enumerate(rows):
                    row_dict = {headers[i]: row[i] if i < len(row) else '' for i in range(len(headers))}
                    row_id = row_dict.get('id', '')
                    
                    if not row_id:
                        continue
                    
                    # Compare with snapshot
                    old_data = snapshot.get(str(row_id), {})
                    changed_fields = {}
                    
                    for field, value in row_dict.items():
                        if field == 'id':
                            continue
                        old_value = str(old_data.get(field, ''))
                        new_value = str(value)
                        if old_value != new_value:
                            changed_fields[field] = value
                    
                    if changed_fields:
                        table_changes.append({
                            'row_id': row_id,
                            'changes': changed_fields
                        })
                        changes_detected += 1
                
                # Sync changes to Bitrix24
                for change in table_changes:
                    try:
                        success = await _update_bitrix24(
                            table_name,
                            change['row_id'],
                            change['changes']
                        )
                        
                        if success:
                            changes_synced += 1
                            details.append({
                                "table": table_name,
                                "id": change['row_id'],
                                "fields": list(change['changes'].keys()),
                                "status": "synced"
                            })
                        else:
                            errors.append(f"Failed to update {table_name} ID {change['row_id']}")
                            
                    except Exception as e:
                        errors.append(f"Error updating {table_name} ID {change['row_id']}: {str(e)}")
                
                # Update snapshot with current data
                new_snapshot = {}
                for row in rows:
                    row_dict = {headers[i]: row[i] if i < len(row) else '' for i in range(len(headers))}
                    if row_dict.get('id'):
                        new_snapshot[str(row_dict['id'])] = row_dict
                
                await _save_snapshot(db, config_id, table_name, new_snapshot)
                
            except Exception as e:
                errors.append(f"Error processing {table_name}: {str(e)}")
                logger.error("sync_from_sheet_table_error", table=table_name, error=str(e))
        
        await sheets_service.close()
        
        return SyncChangesResponse(
            status="completed" if not errors else "completed_with_errors",
            changes_detected=changes_detected,
            changes_synced=changes_synced,
            errors=errors,
            details=details
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("sync_from_sheet_error", error=str(e), config_id=config_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/configs/{config_id}")
async def delete_sync_config(
    config_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete (deactivate) a sync configuration
    """
    try:
        await db.execute(
            text("UPDATE bitrix.sheet_sync_configs SET status = 'deleted', updated_at = :now WHERE id = :id"),
            {"now": datetime.now(), "id": config_id}
        )
        await db.commit()
        
        return {"status": "deleted", "config_id": config_id}
        
    except Exception as e:
        logger.error("delete_sync_config_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions
async def _get_sync_config(db: AsyncSession, config_id: int) -> Optional[Dict]:
    """Get sync config by ID"""
    query = text("""
        SELECT id, sheet_id, sheet_url, tables, access_token, refresh_token,
               sync_interval_minutes, bidirectional, last_sync_at, status
        FROM bitrix.sheet_sync_configs
        WHERE id = :id AND status != 'deleted'
    """)
    result = await db.execute(query, {"id": config_id})
    row = result.fetchone()
    
    if not row:
        return None
    
    return {
        'id': row[0],
        'sheet_id': row[1],
        'sheet_url': row[2],
        'tables': row[3],
        'access_token': row[4],
        'refresh_token': row[5],
        'sync_interval_minutes': row[6],
        'bidirectional': row[7],
        'last_sync_at': row[8],
        'status': row[9]
    }


async def _store_initial_snapshot(db: AsyncSession, config_id: int, config: SheetSyncConfigCreate):
    """Store initial data snapshot for change detection"""
    try:
        sheets_service = GoogleSheetsService(config.access_token)
        
        for table_name in config.tables:
            try:
                sheet_data = await sheets_service.get_values(
                    config.sheet_id,
                    f"{table_name}!A1:ZZ"
                )
                
                if not sheet_data.get('values') or len(sheet_data['values']) < 2:
                    continue
                
                headers = sheet_data['values'][0]
                rows = sheet_data['values'][1:]
                
                snapshot = {}
                for row in rows:
                    row_dict = {headers[i]: row[i] if i < len(row) else '' for i in range(len(headers))}
                    if row_dict.get('id'):
                        snapshot[str(row_dict['id'])] = row_dict
                
                await _save_snapshot(db, config_id, table_name, snapshot)
                
            except Exception as e:
                logger.warning("initial_snapshot_table_error", table=table_name, error=str(e))
        
        await sheets_service.close()
        
    except Exception as e:
        logger.error("store_initial_snapshot_error", error=str(e))


async def _get_snapshot(db: AsyncSession, config_id: int, table_name: str) -> Dict:
    """Get stored snapshot for a table"""
    query = text("""
        SELECT snapshot_data
        FROM bitrix.sheet_sync_snapshots
        WHERE config_id = :config_id AND table_name = :table_name
    """)
    result = await db.execute(query, {"config_id": config_id, "table_name": table_name})
    row = result.fetchone()
    
    if row and row[0]:
        return json.loads(row[0]) if isinstance(row[0], str) else row[0]
    return {}


async def _save_snapshot(db: AsyncSession, config_id: int, table_name: str, snapshot: Dict):
    """Save snapshot for a table"""
    query = text("""
        INSERT INTO bitrix.sheet_sync_snapshots (config_id, table_name, snapshot_data, updated_at)
        VALUES (:config_id, :table_name, :snapshot_data, :updated_at)
        ON CONFLICT (config_id, table_name) 
        DO UPDATE SET snapshot_data = :snapshot_data, updated_at = :updated_at
    """)
    
    await db.execute(query, {
        "config_id": config_id,
        "table_name": table_name,
        "snapshot_data": json.dumps(snapshot),
        "updated_at": datetime.now()
    })
    await db.commit()


async def _update_bitrix24(table_name: str, entity_id: str, fields: Dict[str, Any]) -> bool:
    """Update entity in Bitrix24"""
    import httpx
    
    # Get Bitrix24 webhook URL from environment
    webhook_url = os.getenv('BITRIX_WEBHOOK_URL', '')
    
    if not webhook_url:
        logger.error("bitrix_webhook_url_not_configured")
        return False
    
    api_config = ENTITY_API_MAP.get(table_name)
    if not api_config:
        logger.warning("unsupported_entity_type", table=table_name)
        return False
    
    # Map field names back to Bitrix24 format
    bitrix_fields = _map_fields_to_bitrix(table_name, fields)
    
    try:
        url = f"{webhook_url}/{api_config['method']}"
        payload = {
            "id": entity_id,
            "fields": bitrix_fields
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('result'):
                    logger.info("bitrix_update_success", 
                              table=table_name, 
                              id=entity_id,
                              fields=list(fields.keys()))
                    return True
            
            logger.warning("bitrix_update_failed",
                          table=table_name,
                          id=entity_id,
                          status=response.status_code,
                          response=response.text[:200])
            return False
            
    except Exception as e:
        logger.error("bitrix_update_error", table=table_name, id=entity_id, error=str(e))
        return False


def _map_fields_to_bitrix(table_name: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """Map local field names to Bitrix24 field names"""
    # Common field mappings (lowercase to Bitrix format)
    common_mappings = {
        'name': 'NAME',
        'title': 'TITLE',
        'phone': 'PHONE',
        'email': 'EMAIL',
        'company_id': 'COMPANY_ID',
        'contact_id': 'CONTACT_ID',
        'assigned_by_id': 'ASSIGNED_BY_ID',
        'responsible_id': 'RESPONSIBLE_ID',
        'status_id': 'STATUS_ID',
        'stage_id': 'STAGE_ID',
        'opportunity': 'OPPORTUNITY',
        'comments': 'COMMENTS',
        'source_id': 'SOURCE_ID',
        'source_description': 'SOURCE_DESCRIPTION',
    }
    
    # Table-specific mappings
    table_mappings = {
        'contacts': {
            'first_name': 'NAME',
            'last_name': 'LAST_NAME',
            'second_name': 'SECOND_NAME',
        },
        'deals': {
            'amount': 'OPPORTUNITY',
            'currency': 'CURRENCY_ID',
        },
        'tasks': {
            'title': 'TITLE',
            'description': 'DESCRIPTION',
            'deadline': 'DEADLINE',
            'priority': 'PRIORITY',
        }
    }
    
    result = {}
    mappings = {**common_mappings, **table_mappings.get(table_name, {})}
    
    for field, value in fields.items():
        # Skip internal fields
        if field in ('id', 'created_at', 'updated_at', 'synced_at'):
            continue
        
        bitrix_field = mappings.get(field, field.upper())
        result[bitrix_field] = value
    
    return result
