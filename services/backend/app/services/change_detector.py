"""
Change Detector Service
Detects changes between Google Sheets and local database

Features:
- Compare current sheet data with last synced data
- Identify changed cells with old/new values  
- Track changed rows and columns
- Support for different data types
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from enum import Enum
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.sheet_sync import (
    SheetSyncConfig,
    SheetRowTimestamp,
    FieldMapping,
)
from app.services.google_sheets_api import GoogleSheetsService

logger = structlog.get_logger()


class ChangeType(str, Enum):
    """Type of change detected"""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    UNCHANGED = "unchanged"


class CellChange:
    """Represents a single cell change"""
    
    def __init__(
        self,
        row: int,
        column: int,
        column_name: str,
        old_value: Any,
        new_value: Any,
        change_type: ChangeType,
        bitrix_field: Optional[str] = None,
        is_editable: bool = True,
    ):
        self.row = row
        self.column = column
        self.column_name = column_name
        self.old_value = old_value
        self.new_value = new_value
        self.change_type = change_type
        self.bitrix_field = bitrix_field
        self.is_editable = is_editable
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "row": self.row,
            "column": self.column,
            "column_name": self.column_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "change_type": self.change_type.value,
            "bitrix_field": self.bitrix_field,
            "is_editable": self.is_editable,
        }


class RowChange:
    """Represents changes in a single row"""
    
    def __init__(self, row_number: int, entity_id: Optional[str] = None):
        self.row_number = row_number
        self.entity_id = entity_id
        self.cell_changes: List[CellChange] = []
        self.change_type = ChangeType.UNCHANGED
    
    def add_cell_change(self, cell_change: CellChange):
        self.cell_changes.append(cell_change)
        if cell_change.change_type != ChangeType.UNCHANGED:
            self.change_type = ChangeType.MODIFIED
    
    @property
    def has_changes(self) -> bool:
        return len(self.cell_changes) > 0
    
    @property
    def editable_changes_count(self) -> int:
        return sum(1 for c in self.cell_changes if c.is_editable)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "row_number": self.row_number,
            "entity_id": self.entity_id,
            "change_type": self.change_type.value,
            "cell_changes": [c.to_dict() for c in self.cell_changes],
            "total_changes": len(self.cell_changes),
            "editable_changes": self.editable_changes_count,
        }


class ChangeDetectionResult:
    """Result of change detection operation"""
    
    def __init__(self, config_id: int, sheet_id: str):
        self.config_id = config_id
        self.sheet_id = sheet_id
        self.detected_at = datetime.utcnow()
        self.row_changes: List[RowChange] = []
        self.error: Optional[str] = None
        self.total_rows_scanned = 0
        self.headers: List[str] = []
    
    def add_row_change(self, row_change: RowChange):
        if row_change.has_changes:
            self.row_changes.append(row_change)
    
    @property
    def total_changed_rows(self) -> int:
        return len(self.row_changes)
    
    @property
    def total_changed_cells(self) -> int:
        return sum(len(r.cell_changes) for r in self.row_changes)
    
    @property
    def has_changes(self) -> bool:
        return self.total_changed_rows > 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_id": self.config_id,
            "sheet_id": self.sheet_id,
            "detected_at": self.detected_at.isoformat(),
            "has_changes": self.has_changes,
            "total_rows_scanned": self.total_rows_scanned,
            "total_changed_rows": self.total_changed_rows,
            "total_changed_cells": self.total_changed_cells,
            "headers": self.headers,
            "row_changes": [r.to_dict() for r in self.row_changes],
            "error": self.error,
        }


class ChangeDetector:
    """
    Detects changes between Google Sheets and stored data
    
    Usage:
        detector = ChangeDetector(access_token)
        result = await detector.detect_changes(db, config_id)
    """
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.sheets_service = GoogleSheetsService(access_token)
    
    async def detect_changes(
        self,
        db: AsyncSession,
        config_id: int,
        row_limit: Optional[int] = None,
    ) -> ChangeDetectionResult:
        """
        Detect changes in Google Sheet compared to last synced data
        
        Args:
            db: Database session
            config_id: SheetSyncConfig ID
            row_limit: Optional limit on rows to check (for large sheets)
            
        Returns:
            ChangeDetectionResult with all detected changes
        """
        try:
            # Get config
            stmt = select(SheetSyncConfig).where(SheetSyncConfig.id == config_id)
            result_config = await db.execute(stmt)
            config = result_config.scalars().first()
            
            if not config:
                raise ValueError(f"Config not found: {config_id}")
            
            detection_result = ChangeDetectionResult(
                config_id=config_id,
                sheet_id=config.sheet_id,
            )
            
            # Get field mappings for this config
            stmt_mappings = select(FieldMapping).where(FieldMapping.config_id == config_id)
            result_mappings = await db.execute(stmt_mappings)
            mappings = result_mappings.scalars().all()
            
            # Create mapping lookup: column_index -> mapping info
            column_mappings = {
                m.sheet_column_index: {
                    "column_name": m.sheet_column_name,
                    "bitrix_field": m.bitrix_field,
                    "is_readonly": m.is_readonly or False,
                    "data_type": m.data_type,
                }
                for m in mappings
            }
            
            # Read current sheet data
            sheet_range = f"{config.sheet_name}!A:Z" if config.sheet_name else "A:Z"
            
            try:
                sheet_data = await self.sheets_service.get_values(
                    spreadsheet_id=config.sheet_id,
                    range_name=sheet_range,
                )
            except Exception as e:
                detection_result.error = f"Sheet okuma hatası: {str(e)}"
                logger.error("sheet_read_error", config_id=config_id, error=str(e))
                return detection_result
            
            values = sheet_data.get("values", [])
            
            if not values:
                detection_result.error = "Sheet boş"
                return detection_result
            
            # First row is headers
            headers = values[0] if values else []
            detection_result.headers = headers
            
            # Data rows (skip header)
            data_rows = values[1:]
            
            if row_limit:
                data_rows = data_rows[:row_limit]
            
            detection_result.total_rows_scanned = len(data_rows)
            
            # Get stored row timestamps for comparison
            stmt_timestamps = select(SheetRowTimestamp).where(
                SheetRowTimestamp.config_id == config_id
            )
            result_timestamps = await db.execute(stmt_timestamps)
            timestamps = result_timestamps.scalars().all()
            
            # Create lookup: row_number -> stored data
            stored_data = {
                t.sheet_row_number: t.last_sheet_values or {}
                for t in timestamps
            }
            
            # Compare each row
            for row_idx, row_values in enumerate(data_rows):
                row_number = row_idx + 2  # +2 for 1-indexed and header row
                
                stored_row = stored_data.get(row_number, {})
                entity_id = self._extract_entity_id(row_values, headers, column_mappings)
                
                row_change = RowChange(
                    row_number=row_number,
                    entity_id=entity_id,
                )
                
                # Compare each cell in the row
                for col_idx, cell_value in enumerate(row_values):
                    if col_idx >= len(headers):
                        continue
                    
                    column_name = headers[col_idx]
                    mapping = column_mappings.get(col_idx, {})
                    
                    # Get stored value for this cell
                    stored_value = stored_row.get(column_name)
                    
                    # Normalize values for comparison
                    current_value = self._normalize_value(cell_value)
                    old_value = self._normalize_value(stored_value)
                    
                    # Check if value changed
                    if current_value != old_value:
                        cell_change = CellChange(
                            row=row_number,
                            column=col_idx,
                            column_name=column_name,
                            old_value=old_value,
                            new_value=current_value,
                            change_type=ChangeType.MODIFIED,
                            bitrix_field=mapping.get("bitrix_field"),
                            is_editable=not mapping.get("is_readonly", False),
                        )
                        row_change.add_cell_change(cell_change)
                
                # Check for new rows (no stored data)
                if not stored_row and row_change.has_changes:
                    row_change.change_type = ChangeType.ADDED
                
                detection_result.add_row_change(row_change)
            
            logger.info(
                "change_detection_complete",
                config_id=config_id,
                rows_scanned=detection_result.total_rows_scanned,
                changed_rows=detection_result.total_changed_rows,
                changed_cells=detection_result.total_changed_cells,
            )
            
            return detection_result
            
        except Exception as e:
            logger.error("change_detection_failed", config_id=config_id, error=str(e))
            result = ChangeDetectionResult(config_id, "")
            result.error = str(e)
            return result
    
    async def get_row_details(
        self,
        db: AsyncSession,
        config_id: int,
        row_number: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific row
        
        Args:
            db: Database session
            config_id: Config ID
            row_number: Row number to get details for
            
        Returns:
            Row details with current and stored values
        """
        try:
            # Get config
            stmt = select(SheetSyncConfig).where(SheetSyncConfig.id == config_id)
            result_config = await db.execute(stmt)
            config = result_config.scalars().first()
            
            if not config:
                return None
            
            # Get stored data
            stmt_timestamp = select(SheetRowTimestamp).where(
                and_(
                    SheetRowTimestamp.config_id == config_id,
                    SheetRowTimestamp.sheet_row_number == row_number,
                )
            )
            result_timestamp = await db.execute(stmt_timestamp)
            timestamp = result_timestamp.scalars().first()
            
            # Get current sheet data for this row
            sheet_range = f"{config.sheet_name}!A{row_number}:Z{row_number}"
            
            sheet_data = await self.sheets_service.get_values(
                spreadsheet_id=config.sheet_id,
                range_name=sheet_range,
            )
            
            current_values = sheet_data.get("values", [[]])[0] if sheet_data.get("values") else []
            
            # Get headers
            header_range = f"{config.sheet_name}!A1:Z1"
            header_data = await self.sheets_service.get_values(
                spreadsheet_id=config.sheet_id,
                range_name=header_range,
            )
            headers = header_data.get("values", [[]])[0] if header_data.get("values") else []
            
            # Build comparison
            comparison = []
            stored_values = timestamp.last_sheet_values if timestamp else {}
            
            for idx, header in enumerate(headers):
                current = current_values[idx] if idx < len(current_values) else None
                stored = stored_values.get(header)
                
                comparison.append({
                    "column": idx,
                    "column_name": header,
                    "current_value": current,
                    "stored_value": stored,
                    "is_changed": self._normalize_value(current) != self._normalize_value(stored),
                })
            
            return {
                "row_number": row_number,
                "entity_id": timestamp.entity_id if timestamp else None,
                "last_sync_at": timestamp.last_sync_at.isoformat() if timestamp and timestamp.last_sync_at else None,
                "comparison": comparison,
            }
            
        except Exception as e:
            logger.error("get_row_details_failed", config_id=config_id, row=row_number, error=str(e))
            return None
    
    async def save_snapshot(
        self,
        db: AsyncSession,
        config_id: int,
    ) -> bool:
        """
        Save current sheet state as snapshot for future comparison
        
        Args:
            db: Database session
            config_id: Config ID
            
        Returns:
            True if successful
        """
        try:
            # Get config
            stmt = select(SheetSyncConfig).where(SheetSyncConfig.id == config_id)
            result_config = await db.execute(stmt)
            config = result_config.scalars().first()
            
            if not config:
                return False
            
            # Read current sheet data
            sheet_range = f"{config.sheet_name}!A:Z" if config.sheet_name else "A:Z"
            
            sheet_data = await self.sheets_service.get_values(
                spreadsheet_id=config.sheet_id,
                range_name=sheet_range,
            )
            
            values = sheet_data.get("values", [])
            
            if not values:
                return False
            
            headers = values[0]
            data_rows = values[1:]
            
            # Get field mappings to find ID column
            stmt_mappings = select(FieldMapping).where(FieldMapping.config_id == config_id)
            result_mappings = await db.execute(stmt_mappings)
            mappings = result_mappings.scalars().all()
            
            column_mappings = {
                m.sheet_column_index: {
                    "column_name": m.sheet_column_name,
                    "bitrix_field": m.bitrix_field,
                }
                for m in mappings
            }
            
            # Save each row
            now = datetime.utcnow()
            
            for row_idx, row_values in enumerate(data_rows):
                row_number = row_idx + 2  # +2 for 1-indexed and header row
                
                # Build row data dict
                row_dict = {}
                for col_idx, value in enumerate(row_values):
                    if col_idx < len(headers):
                        row_dict[headers[col_idx]] = value
                
                entity_id = self._extract_entity_id(row_values, headers, column_mappings)
                
                # Check if timestamp exists
                stmt_existing = select(SheetRowTimestamp).where(
                    and_(
                        SheetRowTimestamp.config_id == config_id,
                        SheetRowTimestamp.sheet_row_number == row_number,
                    )
                )
                result_existing = await db.execute(stmt_existing)
                existing = result_existing.scalars().first()
                
                if existing:
                    existing.last_sheet_values = row_dict
                    existing.sheet_modified_at = now
                    existing.last_sync_at = now
                    existing.entity_id = entity_id
                    existing.sync_status = "synced"
                else:
                    new_timestamp = SheetRowTimestamp(
                        config_id=config_id,
                        sheet_row_number=row_number,
                        entity_id=entity_id,
                        sheet_modified_at=now,
                        last_sync_at=now,
                        last_sheet_values=row_dict,
                        sync_status="synced",
                    )
                    db.add(new_timestamp)
            
            await db.commit()
            
            logger.info(
                "snapshot_saved",
                config_id=config_id,
                rows_saved=len(data_rows),
            )
            
            return True
            
        except Exception as e:
            logger.error("save_snapshot_failed", config_id=config_id, error=str(e))
            await db.rollback()
            return False
    
    def _normalize_value(self, value: Any) -> str:
        """Normalize value for comparison"""
        if value is None:
            return ""
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value).strip()
    
    def _extract_entity_id(
        self,
        row_values: List[Any],
        headers: List[str],
        column_mappings: Dict[int, Dict],
    ) -> Optional[str]:
        """Extract entity ID from row values"""
        # Look for ID column in mappings
        for col_idx, mapping in column_mappings.items():
            if mapping.get("bitrix_field", "").upper() == "ID":
                if col_idx < len(row_values):
                    return str(row_values[col_idx]) if row_values[col_idx] else None
        
        # Fallback: look for "ID" in headers
        for idx, header in enumerate(headers):
            if header.upper() == "ID":
                if idx < len(row_values):
                    return str(row_values[idx]) if row_values[idx] else None
        
        return None
    
    async def close(self):
        """Close resources"""
        await self.sheets_service.close()
