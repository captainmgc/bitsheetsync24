"""
Database Models for Sheet Sync functionality
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship

from app.database import Base


class UserSheetsToken(Base):
    """User's Google Sheets OAuth tokens"""

    __tablename__ = "user_sheets_tokens"
    __table_args__ = (Index("idx_user_sheets_tokens_user", "user_id"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), unique=True, nullable=False)
    user_email = Column(String(255))
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text)
    token_expires_at = Column(DateTime)
    scopes = Column(ARRAY(String))
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sync_configs = relationship("SheetSyncConfig", back_populates="user_token")

    __table_args__ = (
        Index("idx_user_sheets_tokens_user", "user_id"),
        Index("idx_user_sheets_tokens_email", "user_email"),
    )


class SheetSyncConfig(Base):
    """Google Sheets Sync Configuration for each user"""

    __tablename__ = "sheet_sync_config"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), ForeignKey("user_sheets_tokens.user_id"), nullable=False)
    sheet_id = Column(String(200), nullable=False)
    sheet_gid = Column(String(50), nullable=False)
    sheet_name = Column(String(255))
    entity_type = Column(String(100))  # "deals", "contacts", "leads", vb
    is_custom_view = Column(Boolean, default=False)
    color_scheme = Column(JSONB)  # {bgColor, textColor}
    webhook_url = Column(String(500))
    webhook_registered = Column(Boolean, default=False)
    last_sync_at = Column(DateTime)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user_token = relationship("UserSheetsToken", back_populates="sync_configs")
    field_mappings = relationship("FieldMapping", back_populates="config")
    sync_logs = relationship("ReverseSyncLog", back_populates="config")
    webhook_events = relationship("WebhookEvent", back_populates="config")

    __table_args__ = (
        Index("idx_sheet_sync_config_user", "user_id"),
    )


class FieldMapping(Base):
    """Auto-detected field mappings: Sheets columns ↔ Bitrix24 fields"""

    __tablename__ = "field_mappings"

    id = Column(Integer, primary_key=True)
    config_id = Column(Integer, ForeignKey("sheet_sync_config.id"), nullable=False)
    sheet_column_index = Column(Integer)  # 0, 1, 2, ...
    sheet_column_name = Column(String(100))  # "Name", "Email", "Phone"
    bitrix_field = Column(String(100))  # "TITLE", "EMAIL", "PHONE"
    data_type = Column(String(50))  # "string", "number", "date", "boolean"
    is_updatable = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    config = relationship("SheetSyncConfig", back_populates="field_mappings")

    __table_args__ = (
        Index("idx_field_mappings_config", "config_id"),
    )


class ReverseSyncLog(Base):
    """Log of all reverse sync operations (Sheets → Bitrix24)"""

    __tablename__ = "reverse_sync_logs"

    id = Column(Integer, primary_key=True)
    config_id = Column(Integer, ForeignKey("sheet_sync_config.id"), nullable=False)
    user_id = Column(String(100), nullable=False)
    entity_id = Column(Integer)  # Bitrix24 entity ID
    sheet_row_id = Column(Integer)  # Google Sheet row number
    changed_fields = Column(JSONB)  # {field: {old: x, new: y}}
    status = Column(String(20), default="pending")  # pending, syncing, completed, failed
    error_message = Column(Text)
    webhook_payload = Column(JSONB)  # Original payload from Google
    synced_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    config = relationship("SheetSyncConfig", back_populates="sync_logs")

    __table_args__ = (
        Index("idx_reverse_sync_logs_config", "config_id"),
        Index("idx_reverse_sync_logs_user", "user_id"),
    )


class WebhookEvent(Base):
    """Webhook events received from Google Apps Script"""

    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True)
    config_id = Column(Integer, ForeignKey("sheet_sync_config.id"), nullable=False)
    event_type = Column(String(50))  # "row_edited", "row_deleted", etc
    event_data = Column(JSONB)
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime)
    received_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    config = relationship("SheetSyncConfig", back_populates="webhook_events")

    __table_args__ = (
        Index("idx_webhook_events_config", "config_id"),
    )
