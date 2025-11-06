"""
Pydantic models for export operations
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ExportStatus(str, Enum):
    """Export status enum"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TableInfo(BaseModel):
    """Table metadata"""
    name: str
    display_name: str
    record_count: int
    size_bytes: int
    has_relationships: bool
    related_tables: List[str] = []


class ExportConfig(BaseModel):
    """Export configuration"""
    tables: List[str] = Field(..., min_length=1, description="Tables to export")
    start_date: Optional[datetime] = Field(None, description="Filter start date")
    end_date: Optional[datetime] = Field(None, description="Filter end date")
    batch_size: int = Field(500, ge=100, le=1000, description="Records per batch")
    include_relationships: bool = Field(True, description="Auto-include related data")
    turkish_columns: bool = Field(True, description="Use Turkish column names")
    separate_datetime: bool = Field(True, description="Split date and time columns")
    sheet_id: Optional[str] = Field(None, description="Google Sheet ID")
    update_mode: str = Field("smart_merge", description="Update strategy: append, upsert, clear_replace, smart_merge")


class ExportCreate(BaseModel):
    """Create export request"""
    config: ExportConfig
    name: Optional[str] = Field(None, description="Export job name")
    description: Optional[str] = Field(None, description="Export job description")


class ExportResponse(BaseModel):
    """Export job response"""
    id: int
    name: Optional[str]
    status: ExportStatus
    config: ExportConfig
    progress: float = Field(0.0, ge=0.0, le=100.0)
    total_records: int = 0
    processed_records: int = 0
    failed_records: int = 0
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ExportLogEntry(BaseModel):
    """Export log entry"""
    id: int
    export_id: int
    level: str  # info, warning, error
    message: str
    details: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class RelationshipInfo(BaseModel):
    """Table relationship information"""
    from_table: str
    to_table: str
    from_column: str
    to_column: str
    relationship_type: str  # one_to_many, many_to_one, many_to_many


class TableStats(BaseModel):
    """Table statistics"""
    table_name: str
    total_records: int
    date_range: Optional[Dict[str, datetime]] = None
    top_values: Optional[Dict[str, List[Any]]] = None
    null_counts: Optional[Dict[str, int]] = None
