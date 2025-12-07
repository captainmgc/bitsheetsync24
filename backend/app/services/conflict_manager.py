"""
Conflict Manager Service
Detects and manages conflicts between Bitrix24 and Google Sheets data

Handles:
- Conflict detection between two data sources
- Conflict resolution strategies
- Conflict history tracking
- Manual conflict resolution support
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import structlog
import httpx

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.orm import selectinload

from app.models.sheet_sync import (
    SheetSyncConfig,
    FieldMapping,
    SheetRowTimestamp,
    ReverseSyncLog,
)
from app.services.google_sheets_api import GoogleSheetsService

logger = structlog.get_logger()


class ConflictType(str, Enum):
    """Types of conflicts"""
    BOTH_MODIFIED = "both_modified"  # Both sides changed
    BITRIX_NEWER = "bitrix_newer"    # Bitrix has newer data
    SHEET_NEWER = "sheet_newer"      # Sheet has newer data
    DELETED_IN_BITRIX = "deleted_in_bitrix"  # Record deleted in Bitrix
    DELETED_IN_SHEET = "deleted_in_sheet"    # Row deleted in Sheet
    

class ResolutionStrategy(str, Enum):
    """Conflict resolution strategies"""
    USE_BITRIX = "use_bitrix"      # Use Bitrix24 value
    USE_SHEET = "use_sheet"        # Use Google Sheets value
    USE_NEWER = "use_newer"        # Use most recently modified
    MERGE = "merge"                # Merge values (if possible)
    MANUAL = "manual"              # Require manual resolution
    SKIP = "skip"                  # Skip this field


@dataclass
class FieldConflict:
    """Represents a conflict in a single field"""
    field_name: str
    column_name: str
    column_index: int
    bitrix_field: str
    bitrix_value: Any
    sheet_value: Any
    bitrix_modified_at: Optional[datetime] = None
    sheet_modified_at: Optional[datetime] = None
    conflict_type: ConflictType = ConflictType.BOTH_MODIFIED
    suggested_resolution: ResolutionStrategy = ResolutionStrategy.MANUAL
    resolved: bool = False
    resolved_value: Any = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None  # 'auto' or 'manual'


@dataclass 
class RowConflict:
    """Represents conflicts in a row"""
    row_number: int
    entity_id: str
    entity_type: str
    detected_at: datetime = field(default_factory=datetime.utcnow)
    field_conflicts: List[FieldConflict] = field(default_factory=list)
    is_resolved: bool = False
    resolution_notes: Optional[str] = None
    
    @property
    def conflict_count(self) -> int:
        return len(self.field_conflicts)
    
    @property
    def unresolved_count(self) -> int:
        return len([f for f in self.field_conflicts if not f.resolved])


@dataclass
class ConflictDetectionResult:
    """Result of conflict detection"""
    config_id: int
    detected_at: datetime = field(default_factory=datetime.utcnow)
    total_rows_checked: int = 0
    conflicts_found: int = 0
    row_conflicts: List[RowConflict] = field(default_factory=list)
    error: Optional[str] = None
    
    @property
    def has_conflicts(self) -> bool:
        return self.conflicts_found > 0


class ConflictManager:
    """
    Manages conflict detection and resolution between Bitrix24 and Google Sheets
    """
    
    def __init__(self, db: AsyncSession, config: SheetSyncConfig):
        self.db = db
        self.config = config
        self.webhook_url = config.webhook_url
        self.sheets_service: Optional[GoogleSheetsService] = None
        
    async def _init_sheets_service(self) -> bool:
        """Initialize Google Sheets service"""
        try:
            # Get user token from config
            user_id = self.config.user_id if hasattr(self.config, 'user_id') else None
            if not user_id:
                logger.error("conflict_manager_no_user_id", config_id=self.config.id)
                return False
                
            self.sheets_service = GoogleSheetsService(self.db, user_id)
            return True
        except Exception as e:
            logger.error("conflict_manager_init_error", error=str(e))
            return False
    
    async def _get_bitrix_entity(self, entity_type: str, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch current entity data from Bitrix24
        """
        try:
            # Map entity type to Bitrix24 method
            method_map = {
                'deals': 'crm.deal.get',
                'contacts': 'crm.contact.get',
                'companies': 'crm.company.get',
                'leads': 'crm.lead.get',
                'tasks': 'tasks.task.get',
            }
            
            method = method_map.get(entity_type)
            if not method:
                logger.warning("conflict_unknown_entity_type", entity_type=entity_type)
                return None
            
            # Build URL
            base_url = self.webhook_url.rstrip('/')
            url = f"{base_url}/{method}"
            
            # Make request
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params={'id': entity_id})
                
                if response.status_code != 200:
                    logger.warning(
                        "conflict_bitrix_fetch_failed",
                        status=response.status_code,
                        entity_type=entity_type,
                        entity_id=entity_id
                    )
                    return None
                
                data = response.json()
                return data.get('result', data)
                
        except Exception as e:
            logger.error(
                "conflict_bitrix_fetch_error",
                entity_type=entity_type,
                entity_id=entity_id,
                error=str(e)
            )
            return None
    
    async def _get_sheet_row(self, row_number: int) -> Optional[List[str]]:
        """
        Fetch current row data from Google Sheets
        """
        try:
            if not self.sheets_service:
                await self._init_sheets_service()
            
            if not self.sheets_service:
                return None
            
            # Get single row
            range_notation = f"'{self.config.sheet_name}'!A{row_number}:ZZ{row_number}"
            values = await self.sheets_service.get_values(
                spreadsheet_id=self.config.sheet_id,
                range_notation=range_notation
            )
            
            if values and len(values) > 0:
                return values[0]
            return None
            
        except Exception as e:
            logger.error(
                "conflict_sheet_fetch_error",
                row_number=row_number,
                error=str(e)
            )
            return None
    
    async def _get_stored_snapshot(self, row_number: int) -> Optional[Dict[str, Any]]:
        """
        Get the stored snapshot for a row
        """
        try:
            stmt = select(SheetRowTimestamp).where(
                and_(
                    SheetRowTimestamp.config_id == self.config.id,
                    SheetRowTimestamp.row_number == row_number
                )
            )
            result = await self.db.execute(stmt)
            timestamp = result.scalars().first()
            
            if timestamp and timestamp.row_data:
                return timestamp.row_data
            return None
            
        except Exception as e:
            logger.error(
                "conflict_snapshot_fetch_error",
                row_number=row_number,
                error=str(e)
            )
            return None
    
    async def detect_conflicts(
        self,
        row_numbers: Optional[List[int]] = None,
        check_all: bool = False
    ) -> ConflictDetectionResult:
        """
        Detect conflicts between Bitrix24 and Google Sheets
        
        Args:
            row_numbers: Specific rows to check (optional)
            check_all: Check all rows with stored timestamps
            
        Returns:
            ConflictDetectionResult with all detected conflicts
        """
        result = ConflictDetectionResult(config_id=self.config.id)
        
        try:
            # Initialize sheets service
            if not await self._init_sheets_service():
                result.error = "Google Sheets servisi başlatılamadı"
                return result
            
            # Get field mappings
            stmt = select(FieldMapping).where(
                FieldMapping.config_id == self.config.id
            )
            mapping_result = await self.db.execute(stmt)
            field_mappings = list(mapping_result.scalars().all())
            
            if not field_mappings:
                result.error = "Alan eşlemeleri bulunamadı"
                return result
            
            # Determine which rows to check
            if row_numbers:
                rows_to_check = row_numbers
            elif check_all:
                # Get all rows with timestamps
                stmt = select(SheetRowTimestamp).where(
                    SheetRowTimestamp.config_id == self.config.id
                )
                ts_result = await self.db.execute(stmt)
                timestamps = list(ts_result.scalars().all())
                rows_to_check = [ts.row_number for ts in timestamps]
            else:
                # Get recently synced rows (last 24 hours)
                cutoff = datetime.utcnow() - timedelta(hours=24)
                stmt = select(SheetRowTimestamp).where(
                    and_(
                        SheetRowTimestamp.config_id == self.config.id,
                        SheetRowTimestamp.last_sync_at >= cutoff
                    )
                )
                ts_result = await self.db.execute(stmt)
                timestamps = list(ts_result.scalars().all())
                rows_to_check = [ts.row_number for ts in timestamps]
            
            result.total_rows_checked = len(rows_to_check)
            
            # Check each row for conflicts
            for row_num in rows_to_check:
                row_conflict = await self._check_row_for_conflicts(
                    row_num, 
                    field_mappings
                )
                if row_conflict and row_conflict.conflict_count > 0:
                    result.row_conflicts.append(row_conflict)
                    result.conflicts_found += row_conflict.conflict_count
            
            logger.info(
                "conflict_detection_complete",
                config_id=self.config.id,
                rows_checked=result.total_rows_checked,
                conflicts_found=result.conflicts_found
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "conflict_detection_error",
                config_id=self.config.id,
                error=str(e)
            )
            result.error = f"Çakışma algılama hatası: {str(e)}"
            return result
    
    async def _check_row_for_conflicts(
        self,
        row_number: int,
        field_mappings: List[FieldMapping]
    ) -> Optional[RowConflict]:
        """
        Check a single row for conflicts
        """
        try:
            # Get stored snapshot
            snapshot = await self._get_stored_snapshot(row_number)
            if not snapshot:
                return None
            
            entity_id = snapshot.get('entity_id')
            if not entity_id:
                return None
            
            # Get current sheet data
            sheet_row = await self._get_sheet_row(row_number)
            if not sheet_row:
                # Row might be deleted in sheet
                return RowConflict(
                    row_number=row_number,
                    entity_id=str(entity_id),
                    entity_type=self.config.entity_type,
                    field_conflicts=[
                        FieldConflict(
                            field_name="ROW",
                            column_name="",
                            column_index=-1,
                            bitrix_field="",
                            bitrix_value=snapshot,
                            sheet_value=None,
                            conflict_type=ConflictType.DELETED_IN_SHEET,
                            suggested_resolution=ResolutionStrategy.MANUAL
                        )
                    ]
                )
            
            # Get current Bitrix data
            bitrix_data = await self._get_bitrix_entity(
                self.config.entity_type,
                str(entity_id)
            )
            if not bitrix_data:
                # Entity might be deleted in Bitrix
                return RowConflict(
                    row_number=row_number,
                    entity_id=str(entity_id),
                    entity_type=self.config.entity_type,
                    field_conflicts=[
                        FieldConflict(
                            field_name="ENTITY",
                            column_name="",
                            column_index=-1,
                            bitrix_field="",
                            bitrix_value=None,
                            sheet_value=sheet_row,
                            conflict_type=ConflictType.DELETED_IN_BITRIX,
                            suggested_resolution=ResolutionStrategy.MANUAL
                        )
                    ]
                )
            
            # Compare field by field
            field_conflicts = []
            stored_data = snapshot.get('data', {})
            
            for mapping in field_mappings:
                if not mapping.is_updatable:
                    continue  # Skip readonly fields
                
                # Get values
                sheet_value = sheet_row[mapping.sheet_column_index] if mapping.sheet_column_index < len(sheet_row) else None
                bitrix_value = bitrix_data.get(mapping.bitrix_field)
                stored_value = stored_data.get(mapping.sheet_column_name)
                
                # Normalize values for comparison
                sheet_value_str = str(sheet_value) if sheet_value is not None else ""
                bitrix_value_str = str(bitrix_value) if bitrix_value is not None else ""
                stored_value_str = str(stored_value) if stored_value is not None else ""
                
                # Check for conflict
                sheet_changed = sheet_value_str != stored_value_str
                bitrix_changed = bitrix_value_str != stored_value_str
                
                if sheet_changed and bitrix_changed:
                    # Both sides changed - real conflict!
                    if sheet_value_str != bitrix_value_str:
                        conflict = FieldConflict(
                            field_name=mapping.sheet_column_name,
                            column_name=mapping.sheet_column_name,
                            column_index=mapping.sheet_column_index,
                            bitrix_field=mapping.bitrix_field,
                            bitrix_value=bitrix_value,
                            sheet_value=sheet_value,
                            conflict_type=ConflictType.BOTH_MODIFIED,
                            suggested_resolution=self._suggest_resolution(
                                mapping, bitrix_value, sheet_value
                            )
                        )
                        field_conflicts.append(conflict)
            
            if field_conflicts:
                return RowConflict(
                    row_number=row_number,
                    entity_id=str(entity_id),
                    entity_type=self.config.entity_type,
                    field_conflicts=field_conflicts
                )
            
            return None
            
        except Exception as e:
            logger.error(
                "conflict_check_row_error",
                row_number=row_number,
                error=str(e)
            )
            return None
    
    def _suggest_resolution(
        self,
        mapping: FieldMapping,
        bitrix_value: Any,
        sheet_value: Any
    ) -> ResolutionStrategy:
        """
        Suggest a resolution strategy based on field type and values
        """
        # For date fields, use the most recent
        if mapping.data_type == 'date':
            return ResolutionStrategy.USE_NEWER
        
        # For numbers, if both are valid, require manual
        if mapping.data_type == 'number':
            return ResolutionStrategy.MANUAL
        
        # For text, prefer non-empty
        if not bitrix_value and sheet_value:
            return ResolutionStrategy.USE_SHEET
        if bitrix_value and not sheet_value:
            return ResolutionStrategy.USE_BITRIX
        
        # Default to manual resolution
        return ResolutionStrategy.MANUAL
    
    async def resolve_conflict(
        self,
        row_number: int,
        field_name: str,
        resolution: ResolutionStrategy,
        custom_value: Any = None
    ) -> Dict[str, Any]:
        """
        Resolve a specific field conflict
        
        Args:
            row_number: Row number with conflict
            field_name: Field name to resolve
            resolution: Resolution strategy to apply
            custom_value: Custom value for MERGE strategy
            
        Returns:
            Resolution result
        """
        try:
            # Get field mapping
            stmt = select(FieldMapping).where(
                and_(
                    FieldMapping.config_id == self.config.id,
                    FieldMapping.sheet_column_name == field_name
                )
            )
            result = await self.db.execute(stmt)
            mapping = result.scalars().first()
            
            if not mapping:
                return {"success": False, "error": f"Alan bulunamadı: {field_name}"}
            
            # Get current values
            sheet_row = await self._get_sheet_row(row_number)
            snapshot = await self._get_stored_snapshot(row_number)
            
            if not snapshot:
                return {"success": False, "error": "Snapshot bulunamadı"}
            
            entity_id = snapshot.get('entity_id')
            bitrix_data = await self._get_bitrix_entity(
                self.config.entity_type,
                str(entity_id)
            )
            
            sheet_value = sheet_row[mapping.sheet_column_index] if sheet_row and mapping.sheet_column_index < len(sheet_row) else None
            bitrix_value = bitrix_data.get(mapping.bitrix_field) if bitrix_data else None
            
            # Determine resolved value
            if resolution == ResolutionStrategy.USE_BITRIX:
                resolved_value = bitrix_value
                target = "sheet"  # Update sheet with Bitrix value
            elif resolution == ResolutionStrategy.USE_SHEET:
                resolved_value = sheet_value
                target = "bitrix"  # Update Bitrix with sheet value
            elif resolution == ResolutionStrategy.MERGE and custom_value is not None:
                resolved_value = custom_value
                target = "both"  # Update both
            elif resolution == ResolutionStrategy.SKIP:
                return {
                    "success": True,
                    "action": "skipped",
                    "message": f"Çakışma atlandı: {field_name}"
                }
            else:
                return {"success": False, "error": "Geçersiz çözüm stratejisi"}
            
            # Apply resolution
            if target in ["sheet", "both"]:
                # Update Google Sheets
                if self.sheets_service:
                    cell_range = f"'{self.config.sheet_name}'!{self._column_letter(mapping.sheet_column_index)}{row_number}"
                    await self.sheets_service.update_values(
                        spreadsheet_id=self.config.sheet_id,
                        range_notation=cell_range,
                        values=[[str(resolved_value) if resolved_value else ""]]
                    )
            
            if target in ["bitrix", "both"]:
                # Update Bitrix24
                from app.services.bitrix_updater import Bitrix24Updater
                updater = Bitrix24Updater(self.webhook_url)
                await updater.update_entity(
                    entity_type=self.config.entity_type,
                    entity_id=str(entity_id),
                    fields={mapping.bitrix_field: resolved_value}
                )
            
            # Update snapshot
            stmt = select(SheetRowTimestamp).where(
                and_(
                    SheetRowTimestamp.config_id == self.config.id,
                    SheetRowTimestamp.row_number == row_number
                )
            )
            result = await self.db.execute(stmt)
            timestamp = result.scalars().first()
            
            if timestamp:
                row_data = timestamp.row_data or {}
                if 'data' not in row_data:
                    row_data['data'] = {}
                row_data['data'][field_name] = resolved_value
                timestamp.row_data = row_data
                timestamp.last_sync_at = datetime.utcnow()
                await self.db.commit()
            
            logger.info(
                "conflict_resolved",
                row_number=row_number,
                field_name=field_name,
                resolution=resolution.value,
                target=target
            )
            
            return {
                "success": True,
                "action": "resolved",
                "field": field_name,
                "resolution": resolution.value,
                "resolved_value": resolved_value,
                "target": target
            }
            
        except Exception as e:
            logger.error(
                "conflict_resolution_error",
                row_number=row_number,
                field_name=field_name,
                error=str(e)
            )
            return {"success": False, "error": str(e)}
    
    async def resolve_row_conflicts(
        self,
        row_number: int,
        resolution: ResolutionStrategy
    ) -> Dict[str, Any]:
        """
        Resolve all conflicts in a row with the same strategy
        
        Args:
            row_number: Row number with conflicts
            resolution: Resolution strategy to apply to all fields
            
        Returns:
            Resolution result
        """
        try:
            # First detect conflicts for this row
            detection = await self.detect_conflicts(row_numbers=[row_number])
            
            if not detection.has_conflicts:
                return {"success": True, "message": "Bu satırda çakışma yok"}
            
            row_conflict = detection.row_conflicts[0] if detection.row_conflicts else None
            if not row_conflict:
                return {"success": True, "message": "Bu satırda çakışma yok"}
            
            results = []
            for field_conflict in row_conflict.field_conflicts:
                result = await self.resolve_conflict(
                    row_number=row_number,
                    field_name=field_conflict.field_name,
                    resolution=resolution
                )
                results.append(result)
            
            successful = sum(1 for r in results if r.get("success"))
            failed = len(results) - successful
            
            return {
                "success": failed == 0,
                "total": len(results),
                "successful": successful,
                "failed": failed,
                "results": results
            }
            
        except Exception as e:
            logger.error(
                "conflict_resolve_row_error",
                row_number=row_number,
                error=str(e)
            )
            return {"success": False, "error": str(e)}
    
    async def get_conflict_history(
        self,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get history of resolved conflicts from sync logs
        """
        try:
            stmt = select(ReverseSyncLog).where(
                ReverseSyncLog.config_id == self.config.id
            ).order_by(desc(ReverseSyncLog.created_at)).limit(limit)
            
            result = await self.db.execute(stmt)
            logs = list(result.scalars().all())
            
            history = []
            for log in logs:
                history.append({
                    "id": log.id,
                    "row_number": log.row_number,
                    "entity_id": log.entity_id,
                    "status": log.status,
                    "changed_fields": log.changed_fields,
                    "error": log.error_message,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                    "synced_at": log.synced_at.isoformat() if log.synced_at else None
                })
            
            return history
            
        except Exception as e:
            logger.error(
                "conflict_history_error",
                config_id=self.config.id,
                error=str(e)
            )
            return []
    
    def _column_letter(self, index: int) -> str:
        """Convert column index to letter (0 = A, 1 = B, etc.)"""
        result = ""
        while index >= 0:
            result = chr(index % 26 + ord('A')) + result
            index = index // 26 - 1
        return result
