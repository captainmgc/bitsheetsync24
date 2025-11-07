"""
Change Processor Service
Processes webhook events and converts sheet changes to Bitrix24 updates
Handles:
- Change detection (what changed?)
- Data transformation (sheet format → Bitrix24 format)
- Error handling and retry logic
"""

import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.sheet_sync import (
    ReverseSyncLog,
    WebhookEvent,
    SheetSyncConfig,
    FieldMapping,
)

logger = structlog.get_logger()


class SyncStatus(str, Enum):
    """Sync operation status"""

    PENDING = "pending"
    SYNCING = "syncing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class ChangeProcessor:
    """
    Process webhook events and generate Bitrix24 updates
    """

    # Bitrix24 entity type configurations
    ENTITY_TYPES = {
        "contacts": {
            "api_method": "crm.contact.update",
            "id_field": "ID",
        },
        "deals": {
            "api_method": "crm.deal.update",
            "id_field": "ID",
        },
        "companies": {
            "api_method": "crm.company.update",
            "id_field": "ID",
        },
        "tasks": {
            "api_method": "crm.task.update",
            "id_field": "ID",
        },
    }

    # Data type converters
    TYPE_CONVERTERS = {
        "string": lambda x: str(x) if x is not None else "",
        "number": lambda x: float(x) if x is not None and str(x).strip() else 0,
        "date": lambda x: str(x) if x is not None else None,
        "boolean": lambda x: str(x).lower() in ["true", "yes", "1", "on"] if x else False,
    }

    def __init__(self):
        """Initialize change processor"""
        pass

    async def process_webhook_event(
        self,
        db: AsyncSession,
        config_id: int,
        user_id: str,
        webhook_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Process incoming webhook event
        
        Args:
            db: Database session
            config_id: SheetSyncConfig ID
            user_id: User ID
            webhook_data: Validated webhook data with changes
            
        Returns:
            Processing result with status
        """
        try:
            # Create webhook event record
            webhook_event = WebhookEvent(
                config_id=config_id,
                event_type=webhook_data.get("event", "row_updated"),
                event_data=webhook_data,
                processed=False,
            )
            db.add(webhook_event)
            await db.flush()

            event_id = webhook_event.id

            # Get config details
            stmt = select(SheetSyncConfig).where(SheetSyncConfig.id == config_id)
            result = await db.execute(stmt)
            config = result.scalars().first()

            if not config:
                raise Exception(f"Config not found: {config_id}")

            # Create reverse sync log entry
            sync_log = ReverseSyncLog(
                config_id=config_id,
                user_id=user_id,
                entity_id=webhook_data.get("entity_id"),
                sheet_row_id=webhook_data.get("row_id"),
                changed_fields=webhook_data.get("changes", {}),
                status=SyncStatus.PENDING.value,
                webhook_payload=webhook_data,
            )
            db.add(sync_log)
            await db.flush()

            log_id = sync_log.id

            logger.info(
                "webhook_event_created",
                event_id=event_id,
                log_id=log_id,
                config_id=config_id,
                changes_count=len(webhook_data.get("changes", {})),
            )

            # Generate Bitrix24 update
            bitrix_update = await self.generate_bitrix_update(
                db=db,
                config=config,
                webhook_data=webhook_data,
                log_id=log_id,
            )

            return {
                "event_id": event_id,
                "log_id": log_id,
                "status": "queued_for_sync",
                "bitrix_update": bitrix_update,
                "entity_type": config.entity_type,
            }

        except Exception as e:
            logger.error(
                "webhook_event_processing_failed",
                config_id=config_id,
                error=str(e),
            )
            raise

    async def generate_bitrix_update(
        self,
        db: AsyncSession,
        config: SheetSyncConfig,
        webhook_data: Dict[str, Any],
        log_id: int,
    ) -> Dict[str, Any]:
        """
        Generate Bitrix24 API update from webhook data
        
        Args:
            db: Database session
            config: SheetSyncConfig record
            webhook_data: Webhook payload with changes
            log_id: ReverseSyncLog ID
            
        Returns:
            Bitrix24 update data
        """
        try:
            entity_type = config.entity_type
            changes = webhook_data.get("changes", {})

            if not changes:
                return {"error": "No changes to process"}

            if entity_type not in self.ENTITY_TYPES:
                raise Exception(f"Unknown entity type: {entity_type}")

            # Get entity config
            entity_config = self.ENTITY_TYPES[entity_type]

            # Get entity ID from webhook
            # Could be: bitrix_id, entity_id, contact_id, deal_id, etc.
            entity_id = webhook_data.get("entity_id") or webhook_data.get("bitrix_id")

            if not entity_id:
                raise Exception("No entity ID in webhook data")

            # Convert field values using mappings
            bitrix_fields = {}

            for bitrix_field, change_data in changes.items():
                new_value = change_data.get("new")

                # Get field mapping to check data type
                stmt = (
                    select(FieldMapping)
                    .where(FieldMapping.config_id == config.id)
                    .where(FieldMapping.bitrix_field == bitrix_field)
                )
                result = await db.execute(stmt)
                mapping = result.scalars().first()

                if mapping and mapping.is_updatable:
                    # Convert value according to data type
                    data_type = mapping.data_type
                    converter = self.TYPE_CONVERTERS.get(data_type, str)

                    try:
                        converted_value = converter(new_value)
                        bitrix_fields[bitrix_field] = converted_value

                        logger.debug(
                            "field_converted",
                            field=bitrix_field,
                            data_type=data_type,
                            old_value=change_data.get("old"),
                            new_value=converted_value,
                        )
                    except Exception as e:
                        logger.warning(
                            "field_conversion_failed",
                            field=bitrix_field,
                            error=str(e),
                        )

            if not bitrix_fields:
                return {"error": "No convertible fields"}

            # Update sync log with converted fields
            stmt = (
                update(ReverseSyncLog)
                .where(ReverseSyncLog.id == log_id)
                .values(changed_fields=bitrix_fields)
            )
            await db.execute(stmt)
            await db.commit()

            bitrix_update = {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "api_method": entity_config["api_method"],
                "fields": bitrix_fields,
                "log_id": log_id,
            }

            logger.info(
                "bitrix_update_generated",
                entity_type=entity_type,
                entity_id=entity_id,
                fields_count=len(bitrix_fields),
            )

            return bitrix_update

        except Exception as e:
            logger.error(
                "generate_bitrix_update_failed",
                config_id=config.id,
                error=str(e),
            )
            raise

    async def mark_sync_status(
        self,
        db: AsyncSession,
        log_id: int,
        status: SyncStatus,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Update sync log status
        
        Args:
            db: Database session
            log_id: ReverseSyncLog ID
            status: New status
            error_message: Error message if failed
            
        Returns:
            Success status
        """
        try:
            update_data = {"status": status.value}

            if error_message:
                update_data["error_message"] = error_message

            stmt = (
                update(ReverseSyncLog)
                .where(ReverseSyncLog.id == log_id)
                .values(**update_data)
            )
            await db.execute(stmt)
            await db.commit()

            logger.info("sync_status_updated", log_id=log_id, status=status.value)
            return True

        except Exception as e:
            logger.error("mark_sync_status_failed", log_id=log_id, error=str(e))
            await db.rollback()
            return False

    async def mark_webhook_event_processed(
        self,
        db: AsyncSession,
        event_id: int,
    ) -> bool:
        """
        Mark webhook event as processed
        
        Args:
            db: Database session
            event_id: WebhookEvent ID
            
        Returns:
            Success status
        """
        try:
            stmt = (
                update(WebhookEvent)
                .where(WebhookEvent.id == event_id)
                .values(
                    processed=True,
                    processed_at=datetime.utcnow(),
                )
            )
            await db.execute(stmt)
            await db.commit()

            logger.info("webhook_event_marked_processed", event_id=event_id)
            return True

        except Exception as e:
            logger.error("mark_webhook_processed_failed", event_id=event_id, error=str(e))
            await db.rollback()
            return False

    async def get_pending_syncs(
        self,
        db: AsyncSession,
        config_id: int,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get pending sync operations
        
        Args:
            db: Database session
            config_id: SheetSyncConfig ID
            limit: Maximum results
            
        Returns:
            List of pending syncs
        """
        try:
            stmt = (
                select(ReverseSyncLog)
                .where(ReverseSyncLog.config_id == config_id)
                .where(
                    ReverseSyncLog.status.in_(
                        [SyncStatus.PENDING.value, SyncStatus.RETRYING.value]
                    )
                )
                .order_by(ReverseSyncLog.created_at)
                .limit(limit)
            )

            result = await db.execute(stmt)
            logs = result.scalars().all()

            pending_list = [
                {
                    "id": log.id,
                    "entity_id": log.entity_id,
                    "row_id": log.sheet_row_id,
                    "changes": log.changed_fields,
                    "status": log.status,
                    "created_at": log.created_at.isoformat(),
                }
                for log in logs
            ]

            return pending_list

        except Exception as e:
            logger.error("get_pending_syncs_failed", config_id=config_id, error=str(e))
            return []

    async def get_sync_history(
        self,
        db: AsyncSession,
        config_id: int,
        status: Optional[SyncStatus] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get sync history for a config
        
        Args:
            db: Database session
            config_id: SheetSyncConfig ID
            status: Filter by status
            limit: Maximum results
            
        Returns:
            Sync history
        """
        try:
            stmt = select(ReverseSyncLog).where(ReverseSyncLog.config_id == config_id)

            if status:
                stmt = stmt.where(ReverseSyncLog.status == status.value)

            stmt = stmt.order_by(ReverseSyncLog.created_at.desc()).limit(limit)

            result = await db.execute(stmt)
            logs = result.scalars().all()

            history = [
                {
                    "id": log.id,
                    "entity_id": log.entity_id,
                    "row_id": log.sheet_row_id,
                    "status": log.status,
                    "changes": log.changed_fields,
                    "error": log.error_message,
                    "created_at": log.created_at.isoformat(),
                    "updated_at": log.updated_at.isoformat() if log.updated_at else None,
                }
                for log in logs
            ]

            return history

        except Exception as e:
            logger.error("get_sync_history_failed", config_id=config_id, error=str(e))
            return []
