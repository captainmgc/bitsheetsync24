"""
Pydantic v2 Schemas for Export Operations
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ExportStatus(str, Enum):
    """Export operation status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExportType(str, Enum):
    """Type of export operation"""
    FULL = "full"
    INCREMENTAL = "incremental"
    DATE_RANGE = "date_range"
    CUSTOM_VIEW = "custom_view"


class DateRangeFilter(BaseModel):
    """Date range filter for exports"""
    date_from: datetime
    date_to: datetime
    date_field: str = Field(default="DATE_MODIFY", description="Field to filter on")


class ColumnMapping(BaseModel):
    """Column name mapping for Turkish export"""
    source_field: str
    target_name: str
    is_date: bool = False
    is_time: bool = False


class ExportConfigCreate(BaseModel):
    """Configuration for creating a new export"""
    model_config = ConfigDict(use_enum_values=True)
    
    # Required
    entity_name: str = Field(..., description="Table name (leads, tasks, etc.)")
    export_type: ExportType = Field(default=ExportType.FULL)
    
    # Optional Filters
    date_range: Optional[DateRangeFilter] = None
    custom_filter: Optional[Dict[str, Any]] = None
    
    # Related Tables (auto-detected if None)
    include_related: bool = Field(default=True, description="Auto-include related tables")
    related_entities: Optional[List[str]] = None
    
    # Column Configuration
    column_mappings: Optional[List[ColumnMapping]] = None
    use_turkish_names: bool = Field(default=True)
    separate_date_time: bool = Field(default=True)
    
    # Batch Settings
    batch_size: int = Field(default=500, ge=1, le=1000)
    
    # Google Sheets
    sheet_url: Optional[str] = None
    sheet_gid: Optional[str] = Field(default="0")
    
    # Metadata
    created_by: Optional[str] = None


class ExportConfigResponse(BaseModel):
    """Response schema for export configuration"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    export_type: ExportType
    entity_name: str
    status: ExportStatus
    
    # Progress
    total_records: int = 0
    processed_records: int = 0
    failed_records: int = 0
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    
    # Results
    sheet_url: Optional[str] = None
    error_message: Optional[str] = None
    
    created_at: datetime


class ExportProgressUpdate(BaseModel):
    """Real-time progress update"""
    export_id: int
    status: ExportStatus
    processed_records: int
    total_records: int
    current_batch: int
    total_batches: int
    progress_percentage: float
    estimated_time_remaining: Optional[int] = None  # seconds


class ExportListResponse(BaseModel):
    """List of exports with pagination"""
    exports: List[ExportConfigResponse]
    total: int
    page: int
    page_size: int


class TableMetadata(BaseModel):
    """Metadata about a database table"""
    name: str
    display_name: str
    record_count: int
    last_updated: Optional[datetime]
    columns: List[Dict[str, Any]]
    foreign_keys: List[Dict[str, str]]  # {"column": "COMPANY_ID", "references": "companies"}


class RelationshipInfo(BaseModel):
    """Automatically detected relationships"""
    source_table: str
    target_table: str
    source_column: str
    target_column: str
    relationship_type: str  # "one_to_many", "many_to_one", etc.
