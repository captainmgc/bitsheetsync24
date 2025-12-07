"""
Google Sheets Export Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class DateRangeFilter(BaseModel):
    """Date range filter for export"""
    from_date: str = Field(..., alias="from")
    to_date: str = Field(..., alias="to")


class SheetsExportRequest(BaseModel):
    """Request schema for Google Sheets export"""
    tables: List[str] = Field(..., description="List of table names to export")
    date_range: Optional[DateRangeFilter] = Field(None, alias="dateRange", description="Optional date range filter")
    sheet_mode: str = Field(..., alias="sheetMode", description="'new' or 'existing'")
    sheet_name: Optional[str] = Field(None, alias="sheetName", description="Name for new sheet")
    sheet_id: Optional[str] = Field(None, alias="sheetId", description="ID of existing sheet")
    access_token: str = Field(..., alias="accessToken", description="Google OAuth access token")
    table_views: Optional[Dict[str, int]] = Field(None, alias="tableViews", description="Map of table_name -> view_id")
    # Bidirectional sync options
    enable_sync: bool = Field(False, alias="enableSync", description="Enable incremental sync after export")
    bidirectional: bool = Field(False, description="Enable bidirectional sync (Sheet → Bitrix24)")
    sync_interval_minutes: int = Field(5, alias="syncIntervalMinutes", description="Auto-sync interval")
    refresh_token: Optional[str] = Field(None, alias="refreshToken", description="Google OAuth refresh token")
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }



class SheetsExportResponse(BaseModel):
    """Response schema for Google Sheets export"""
    status: str = Field(..., description="Export status")
    sheet_url: str = Field(..., description="URL to the Google Sheet")
    sheet_id: str = Field(..., description="Google Sheet ID")
    total_rows: int = Field(..., description="Total rows exported")
    tables_exported: List[str] = Field(..., description="List of exported table names")
    export_id: int = Field(..., description="Internal export log ID")
    created_at: datetime = Field(..., description="Export timestamp")
    sync_config_id: Optional[int] = Field(None, description="Sync configuration ID for bidirectional sync")


class TableExportStats(BaseModel):
    """Statistics for a single table export"""
    table_name: str
    rows_exported: int
    columns: int
    sheet_name: str
    errors: List[str] = Field(default_factory=list)


# Bidirectional Sync Schemas
class SheetSyncConfigCreate(BaseModel):
    """Create sync configuration for bidirectional sync"""
    sheet_id: str = Field(..., alias="sheetId", description="Google Sheet ID")
    sheet_url: str = Field(..., alias="sheetUrl", description="Google Sheet URL")
    tables: List[str] = Field(..., description="Tables included in sync")
    access_token: str = Field(..., alias="accessToken", description="Google OAuth access token")
    refresh_token: Optional[str] = Field(None, alias="refreshToken", description="Google OAuth refresh token")
    sync_interval_minutes: int = Field(5, alias="syncIntervalMinutes", description="Auto-sync interval in minutes")
    bidirectional: bool = Field(True, description="Enable bidirectional sync")
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }


class SheetSyncConfigResponse(BaseModel):
    """Sync configuration response"""
    id: int
    sheet_id: str
    sheet_url: str
    tables: List[str]
    sync_interval_minutes: int
    bidirectional: bool
    last_sync_at: Optional[datetime] = None
    next_sync_at: Optional[datetime] = None
    status: str = "active"
    created_at: datetime
    updated_at: Optional[datetime] = None


class SheetChangeDetection(BaseModel):
    """Detected changes from Google Sheet"""
    table_name: str
    row_id: int
    changes: Dict[str, Any]
    change_type: str  # 'update', 'insert', 'delete'


class SyncChangesRequest(BaseModel):
    """Request to sync changes from Google Sheets to Bitrix24"""
    sync_config_id: int = Field(..., alias="syncConfigId")
    access_token: str = Field(..., alias="accessToken")
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }


class SyncChangesResponse(BaseModel):
    """Response from syncing changes"""
    status: str
    changes_detected: int
    changes_synced: int
    errors: List[str] = Field(default_factory=list)
    details: List[Dict[str, Any]] = Field(default_factory=list)

