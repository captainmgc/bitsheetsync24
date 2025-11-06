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
    date_range: Optional[DateRangeFilter] = Field(None, description="Optional date range filter")
    sheet_mode: str = Field(..., description="'new' or 'existing'")
    sheet_name: Optional[str] = Field(None, description="Name for new sheet")
    sheet_id: Optional[str] = Field(None, description="ID of existing sheet")
    access_token: str = Field(..., description="Google OAuth access token")
    table_views: Optional[Dict[str, int]] = Field(None, description="Map of table_name -> view_id")
    
    class Config:
        populate_by_name = True


class SheetsExportResponse(BaseModel):
    """Response schema for Google Sheets export"""
    status: str = Field(..., description="Export status")
    sheet_url: str = Field(..., description="URL to the Google Sheet")
    sheet_id: str = Field(..., description="Google Sheet ID")
    total_rows: int = Field(..., description="Total rows exported")
    tables_exported: List[str] = Field(..., description="List of exported table names")
    export_id: int = Field(..., description="Internal export log ID")
    created_at: datetime = Field(..., description="Export timestamp")


class TableExportStats(BaseModel):
    """Statistics for a single table export"""
    table_name: str
    rows_exported: int
    columns: int
    sheet_name: str
    errors: List[str] = Field(default_factory=list)
