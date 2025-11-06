"""
Export Log Models
Tracks all export operations and their status
"""
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, Boolean, Enum as SQLEnum
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

from app.database import Base


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


class ExportLog(Base):
    """Log table for export operations"""
    __tablename__ = "export_logs"
    __table_args__ = {'schema': 'bitrix'}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Export Configuration
    export_type = Column(SQLEnum(ExportType), nullable=False)
    entity_name = Column(String(100), nullable=False)  # leads, tasks, custom_view_123
    
    # Date Range (for date_range export type)
    date_from = Column(DateTime, nullable=True)
    date_to = Column(DateTime, nullable=True)
    
    # Related Tables (for automatic relationship detection)
    related_entities = Column(JSON, nullable=True)  # ["contacts", "companies", "users"]
    
    # Export Configuration
    config = Column(JSON, nullable=False)  # Full export configuration
    
    # Status Tracking
    status = Column(SQLEnum(ExportStatus), default=ExportStatus.PENDING, nullable=False)
    
    # Progress Tracking
    total_records = Column(Integer, default=0)
    processed_records = Column(Integer, default=0)
    failed_records = Column(Integer, default=0)
    
    # Batch Information
    total_batches = Column(Integer, default=0)
    completed_batches = Column(Integer, default=0)
    batch_size = Column(Integer, default=500)
    
    # Google Sheets Information
    sheet_url = Column(String(500), nullable=True)
    sheet_id = Column(String(200), nullable=True)
    sheet_gid = Column(String(50), nullable=True)
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Error Information
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    
    # Webhook Trigger (if triggered by Bitrix24 webhook)
    triggered_by_webhook = Column(Boolean, default=False)
    webhook_event_type = Column(String(100), nullable=True)
    webhook_entity_id = Column(Integer, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(100), nullable=True)  # User ID or "system"


class ExportBatchLog(Base):
    """Detailed log for each batch in an export"""
    __tablename__ = "export_batch_logs"
    __table_args__ = {'schema': 'bitrix'}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    export_log_id = Column(Integer, nullable=False)  # FK to export_logs.id
    
    batch_number = Column(Integer, nullable=False)
    batch_size = Column(Integer, nullable=False)
    
    # Status
    status = Column(SQLEnum(ExportStatus), default=ExportStatus.PENDING, nullable=False)
    
    # Records
    record_ids = Column(JSON, nullable=True)  # List of record IDs in this batch
    records_processed = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Error Information
    error_message = Column(Text, nullable=True)
    errors = Column(JSON, nullable=True)  # List of individual record errors
    
    # Retry Information
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
