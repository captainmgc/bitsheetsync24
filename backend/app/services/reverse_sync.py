"""
Reverse Sync Service
Handles sending changes from Google Sheets to Bitrix24

Features:
- Single row sync
- Batch sync for multiple rows
- Selective field sync
- Sync status tracking
- Error handling and notifications
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import asyncio
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_

from app.models.sheet_sync import (
    SheetSyncConfig,
    FieldMapping,
    ReverseSyncLog,
    SheetRowTimestamp,
)
from app.services.change_detector import ChangeDetector, ChangeDetectionResult, RowChange
from app.config import settings

logger = structlog.get_logger()


class SyncDirection(str, Enum):
    """Sync direction"""
    SHEET_TO_BITRIX = "sheet_to_bitrix"
    BITRIX_TO_SHEET = "bitrix_to_sheet"


class SyncResult:
    """Result of a sync operation"""
    
    def __init__(self, row_number: int, entity_id: Optional[str] = None):
        self.row_number = row_number
        self.entity_id = entity_id
        self.success = False
        self.error: Optional[str] = None
        self.fields_synced: List[str] = []
        self.synced_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "row_number": self.row_number,
            "entity_id": self.entity_id,
            "success": self.success,
            "error": self.error,
            "fields_synced": self.fields_synced,
            "synced_at": self.synced_at.isoformat() if self.synced_at else None,
        }


class BatchSyncResult:
    """Result of a batch sync operation"""
    
    def __init__(self):
        self.started_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None
        self.total_rows = 0
        self.successful = 0
        self.failed = 0
        self.skipped = 0
        self.results: List[SyncResult] = []
        self.error: Optional[str] = None
    
    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None
    
    def add_result(self, result: SyncResult):
        self.results.append(result)
        self.total_rows += 1
        if result.success:
            self.successful += 1
        elif result.error:
            self.failed += 1
        else:
            self.skipped += 1
    
    def complete(self):
        self.completed_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_rows": self.total_rows,
            "successful": self.successful,
            "failed": self.failed,
            "skipped": self.skipped,
            "results": [r.to_dict() for r in self.results],
            "error": self.error,
        }


class ReverseSyncService:
    """
    Service for syncing changes from Google Sheets to Bitrix24
    """
    
    # Bitrix24 API method mappings
    ENTITY_API_METHODS = {
        "contacts": "crm.contact.update",
        "deals": "crm.deal.update",
        "companies": "crm.company.update",
        "leads": "crm.lead.update",
        "tasks": "tasks.task.update",
        "activities": "crm.activity.update",
    }
    
    def __init__(self, bitrix_webhook_url: str, access_token: Optional[str] = None):
        """
        Initialize reverse sync service
        
        Args:
            bitrix_webhook_url: Bitrix24 webhook URL for API calls
            access_token: Google Sheets access token (optional, for reading sheet data)
        """
        self.bitrix_webhook_url = bitrix_webhook_url
        self.access_token = access_token
        self.timeout = 30
    
    async def sync_single_row(
        self,
        db: AsyncSession,
        config_id: int,
        row_number: int,
        changes: Dict[str, Any],
        entity_id: str,
    ) -> SyncResult:
        """
        Sync a single row to Bitrix24
        
        Args:
            db: Database session
            config_id: Config ID
            row_number: Sheet row number
            changes: Dictionary of field changes {field_name: new_value}
            entity_id: Bitrix24 entity ID
            
        Returns:
            SyncResult with status
        """
        result = SyncResult(row_number=row_number, entity_id=entity_id)
        
        try:
            # Get config
            stmt = select(SheetSyncConfig).where(SheetSyncConfig.id == config_id)
            config_result = await db.execute(stmt)
            config = config_result.scalars().first()
            
            if not config:
                result.error = "Yapılandırma bulunamadı"
                return result
            
            entity_type = config.entity_type
            
            if entity_type not in self.ENTITY_API_METHODS:
                result.error = f"Desteklenmeyen entity tipi: {entity_type}"
                return result
            
            # Get field mappings to translate sheet columns to Bitrix fields
            stmt_mappings = select(FieldMapping).where(
                and_(
                    FieldMapping.config_id == config_id,
                    FieldMapping.is_readonly == False,
                )
            )
            mapping_result = await db.execute(stmt_mappings)
            mappings = mapping_result.scalars().all()
            
            # Create mapping lookup
            column_to_bitrix = {m.sheet_column_name: m.bitrix_field for m in mappings}
            
            # Prepare Bitrix update fields
            bitrix_fields = {}
            for column_name, new_value in changes.items():
                bitrix_field = column_to_bitrix.get(column_name)
                if bitrix_field:
                    bitrix_fields[bitrix_field] = new_value
                    result.fields_synced.append(column_name)
            
            if not bitrix_fields:
                result.error = "Güncellenebilir alan bulunamadı"
                return result
            
            # Create sync log
            sync_log = ReverseSyncLog(
                config_id=config_id,
                user_id=config.user_id,
                entity_id=int(entity_id) if entity_id else None,
                sheet_row_id=row_number,
                changed_fields=changes,
                status="syncing",
            )
            db.add(sync_log)
            await db.flush()
            
            # Call Bitrix24 API
            import httpx
            
            api_method = self.ENTITY_API_METHODS[entity_type]
            url = f"{self.bitrix_webhook_url}/{api_method}"
            
            payload = {
                "id": entity_id,
                "fields": bitrix_fields,
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    timeout=self.timeout,
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    
                    if response_data.get("result"):
                        result.success = True
                        result.synced_at = datetime.utcnow()
                        sync_log.status = "completed"
                        sync_log.synced_at = result.synced_at
                        
                        # Update row timestamp
                        await self._update_row_timestamp(
                            db, config_id, row_number, entity_id, changes
                        )
                    else:
                        error_desc = response_data.get("error_description", "Bilinmeyen hata")
                        result.error = f"Bitrix24 hatası: {error_desc}"
                        sync_log.status = "failed"
                        sync_log.error_message = result.error
                else:
                    result.error = f"HTTP hatası: {response.status_code}"
                    sync_log.status = "failed"
                    sync_log.error_message = result.error
            
            await db.commit()
            
            logger.info(
                "single_row_sync_completed",
                config_id=config_id,
                row_number=row_number,
                entity_id=entity_id,
                success=result.success,
            )
            
            return result
            
        except Exception as e:
            result.error = str(e)
            logger.error(
                "single_row_sync_failed",
                config_id=config_id,
                row_number=row_number,
                error=str(e),
            )
            return result
    
    async def sync_selected_rows(
        self,
        db: AsyncSession,
        config_id: int,
        row_changes: List[RowChange],
        concurrent_limit: int = 5,
    ) -> BatchSyncResult:
        """
        Sync selected rows to Bitrix24
        
        Args:
            db: Database session
            config_id: Config ID
            row_changes: List of row changes to sync
            concurrent_limit: Max concurrent API calls
            
        Returns:
            BatchSyncResult with all results
        """
        batch_result = BatchSyncResult()
        
        try:
            # Process rows in batches
            for i in range(0, len(row_changes), concurrent_limit):
                batch = row_changes[i:i + concurrent_limit]
                
                # Create tasks for this batch
                tasks = []
                for row_change in batch:
                    # Convert cell changes to dict
                    changes = {
                        cell.column_name: cell.new_value
                        for cell in row_change.cell_changes
                        if cell.is_editable
                    }
                    
                    if changes and row_change.entity_id:
                        tasks.append(
                            self.sync_single_row(
                                db=db,
                                config_id=config_id,
                                row_number=row_change.row_number,
                                changes=changes,
                                entity_id=row_change.entity_id,
                            )
                        )
                    else:
                        # Skip rows without changes or entity ID
                        skip_result = SyncResult(
                            row_number=row_change.row_number,
                            entity_id=row_change.entity_id,
                        )
                        if not row_change.entity_id:
                            skip_result.error = "Entity ID bulunamadı"
                        batch_result.add_result(skip_result)
                
                # Execute batch
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for result in results:
                        if isinstance(result, Exception):
                            error_result = SyncResult(row_number=0)
                            error_result.error = str(result)
                            batch_result.add_result(error_result)
                        else:
                            batch_result.add_result(result)
                
                # Rate limiting between batches
                if i + concurrent_limit < len(row_changes):
                    await asyncio.sleep(0.5)
            
            batch_result.complete()
            
            logger.info(
                "batch_sync_completed",
                config_id=config_id,
                total=batch_result.total_rows,
                successful=batch_result.successful,
                failed=batch_result.failed,
            )
            
            return batch_result
            
        except Exception as e:
            batch_result.error = str(e)
            batch_result.complete()
            logger.error("batch_sync_failed", config_id=config_id, error=str(e))
            return batch_result
    
    async def sync_all_changes(
        self,
        db: AsyncSession,
        config_id: int,
        detection_result: ChangeDetectionResult,
    ) -> BatchSyncResult:
        """
        Sync all detected changes to Bitrix24
        
        Args:
            db: Database session
            config_id: Config ID
            detection_result: Result from change detection
            
        Returns:
            BatchSyncResult with all results
        """
        if not detection_result.has_changes:
            result = BatchSyncResult()
            result.complete()
            return result
        
        # Filter to only rows with editable changes
        rows_to_sync = [
            row for row in detection_result.row_changes
            if row.editable_changes_count > 0 and row.entity_id
        ]
        
        return await self.sync_selected_rows(db, config_id, rows_to_sync)
    
    async def _update_row_timestamp(
        self,
        db: AsyncSession,
        config_id: int,
        row_number: int,
        entity_id: str,
        synced_values: Dict[str, Any],
    ):
        """Update row timestamp after successful sync"""
        try:
            stmt = select(SheetRowTimestamp).where(
                and_(
                    SheetRowTimestamp.config_id == config_id,
                    SheetRowTimestamp.sheet_row_number == row_number,
                )
            )
            result = await db.execute(stmt)
            timestamp = result.scalars().first()
            
            now = datetime.utcnow()
            
            if timestamp:
                # Update existing values
                current_values = timestamp.last_sheet_values or {}
                current_values.update(synced_values)
                
                timestamp.last_sheet_values = current_values
                timestamp.last_sync_at = now
                timestamp.bitrix_modified_at = now
                timestamp.sync_status = "synced"
            else:
                # Create new timestamp
                new_timestamp = SheetRowTimestamp(
                    config_id=config_id,
                    sheet_row_number=row_number,
                    entity_id=entity_id,
                    last_sheet_values=synced_values,
                    last_sync_at=now,
                    bitrix_modified_at=now,
                    sync_status="synced",
                )
                db.add(new_timestamp)
            
            await db.flush()
            
        except Exception as e:
            logger.error(
                "update_row_timestamp_failed",
                config_id=config_id,
                row_number=row_number,
                error=str(e),
            )
    
    async def get_sync_history(
        self,
        db: AsyncSession,
        config_id: int,
        status_filter: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get sync history for a config
        
        Args:
            db: Database session
            config_id: Config ID
            status_filter: Optional status filter (pending, syncing, completed, failed)
            limit: Max results
            
        Returns:
            List of sync log entries
        """
        try:
            stmt = select(ReverseSyncLog).where(
                ReverseSyncLog.config_id == config_id
            )
            
            if status_filter:
                stmt = stmt.where(ReverseSyncLog.status == status_filter)
            
            stmt = stmt.order_by(ReverseSyncLog.created_at.desc()).limit(limit)
            
            result = await db.execute(stmt)
            logs = result.scalars().all()
            
            return [
                {
                    "id": log.id,
                    "entity_id": log.entity_id,
                    "row_number": log.sheet_row_id,
                    "status": log.status,
                    "changed_fields": log.changed_fields,
                    "error": log.error_message,
                    "created_at": log.created_at.isoformat(),
                    "synced_at": log.synced_at.isoformat() if log.synced_at else None,
                }
                for log in logs
            ]
            
        except Exception as e:
            logger.error("get_sync_history_failed", config_id=config_id, error=str(e))
            return []
    
    async def retry_failed_rows(
        self,
        db: AsyncSession,
        config_id: int,
        log_ids: Optional[List[int]] = None,
    ) -> BatchSyncResult:
        """
        Retry failed sync operations
        
        Args:
            db: Database session
            config_id: Config ID
            log_ids: Optional specific log IDs to retry
            
        Returns:
            BatchSyncResult
        """
        batch_result = BatchSyncResult()
        
        try:
            stmt = select(ReverseSyncLog).where(
                and_(
                    ReverseSyncLog.config_id == config_id,
                    ReverseSyncLog.status == "failed",
                )
            )
            
            if log_ids:
                stmt = stmt.where(ReverseSyncLog.id.in_(log_ids))
            
            stmt = stmt.limit(50)
            
            result = await db.execute(stmt)
            failed_logs = result.scalars().all()
            
            for log in failed_logs:
                if log.entity_id and log.changed_fields:
                    sync_result = await self.sync_single_row(
                        db=db,
                        config_id=config_id,
                        row_number=log.sheet_row_id or 0,
                        changes=log.changed_fields,
                        entity_id=str(log.entity_id),
                    )
                    batch_result.add_result(sync_result)
            
            batch_result.complete()
            return batch_result
            
        except Exception as e:
            batch_result.error = str(e)
            batch_result.complete()
            logger.error("retry_failed_rows_failed", config_id=config_id, error=str(e))
            return batch_result
