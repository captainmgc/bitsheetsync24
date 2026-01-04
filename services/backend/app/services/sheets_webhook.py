"""
Google Sheets Webhook Management Service
Handles webhook registration, updates, and deregistration for Google Sheets
"""

import httpx
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.config import settings
from app.models.sheet_sync import SheetSyncConfig, FieldMapping
from app.services.field_detector import FieldDetector

logger = structlog.get_logger()


class SheetsWebhookManager:
    """
    Manages webhook registration for Google Sheets
    - Reads sheet headers and auto-detects fields
    - Registers webhook with Google Apps Script
    - Updates webhook configurations
    - Handles webhook events
    """

    def __init__(self, access_token: str):
        """
        Initialize with user's access token
        
        Args:
            access_token: Valid Google API access token
        """
        self.access_token = access_token
        self.sheets_api_url = "https://sheets.googleapis.com/v4/spreadsheets"
        self.headers = {"Authorization": f"Bearer {access_token}"}

    async def get_sheet_headers(self, sheet_id: str, gid: str) -> List[str]:
        """
        Read first row (headers) from Google Sheet
        
        Args:
            sheet_id: Google Sheet ID
            gid: Sheet tab ID (gid parameter)
            
        Returns:
            List of header values
        """
        try:
            url = f"{self.sheets_api_url}/{sheet_id}/values/'{gid}'!A1:Z1"

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    params={"majorDimension": "ROWS"},
                    timeout=10,
                )
                response.raise_for_status()
                data = response.json()

            values = data.get("values", [])
            headers = values[0] if values else []

            logger.info("sheet_headers_read", sheet_id=sheet_id, gid=gid, count=len(headers))
            return headers

        except httpx.HTTPError as e:
            logger.error("sheet_headers_read_failed", sheet_id=sheet_id, error=str(e))
            raise Exception(f"Failed to read sheet headers: {str(e)}")

    async def auto_detect_and_save_mappings(
        self,
        db: AsyncSession,
        config_id: int,
        headers: List[str],
    ) -> Dict[str, Any]:
        """
        Auto-detect field mappings from headers and save to database
        
        Args:
            db: Database session
            config_id: SheetSyncConfig ID
            headers: List of sheet headers
            
        Returns:
            Validation result with mappings
        """
        try:
            # Auto-detect mappings
            detected_mappings = FieldDetector.auto_detect_mappings(headers)
            validation_result = FieldDetector.validate_mappings(detected_mappings)

            # Save to database
            for mapping in detected_mappings:
                if mapping["bitrix_field"]:  # Only save mapped fields
                    field_mapping = FieldMapping(
                        config_id=config_id,
                        sheet_column_index=mapping["sheet_column_index"],
                        sheet_column_name=mapping["sheet_column_name"],
                        bitrix_field=mapping["bitrix_field"],
                        data_type=mapping["data_type"],
                        is_updatable=True,
                    )
                    db.add(field_mapping)

            await db.commit()

            logger.info(
                "field_mappings_saved",
                config_id=config_id,
                total=len(headers),
                mapped=validation_result["mapped_fields"],
            )

            return validation_result

        except Exception as e:
            logger.error("auto_detect_mappings_failed", config_id=config_id, error=str(e))
            await db.rollback()
            raise

    async def register_webhook(
        self,
        db: AsyncSession,
        config_id: int,
        user_id: str,
        sheet_id: str,
        gid: str,
        entity_type: str,
    ) -> Dict[str, Any]:
        """
        Register webhook for a Google Sheet
        
        Flow:
        1. Read sheet headers
        2. Auto-detect field mappings
        3. Generate webhook URL
        4. Add webhook registration record
        
        Args:
            db: Database session
            config_id: SheetSyncConfig ID
            user_id: Google user ID
            sheet_id: Google Sheet ID
            gid: Sheet tab ID
            entity_type: Bitrix24 entity type (deals, contacts, etc)
            
        Returns:
            Webhook registration details
        """
        try:
            # Step 1: Read headers
            headers = await self.get_sheet_headers(sheet_id, gid)

            if not headers:
                raise Exception("Sheet has no headers in first row")

            # Step 2: Auto-detect and save mappings
            mapping_result = await self.auto_detect_and_save_mappings(
                db, config_id, headers
            )

            # Step 3: Generate webhook URL
            # Webhook URL format: /api/v1/sheet-sync/webhook/{config_id}
            webhook_url = f"{settings.api_host}:{settings.api_port}/api/v1/sheet-sync/webhook/{config_id}"

            # Step 4: Update config in database
            stmt = (
                update(SheetSyncConfig)
                .where(SheetSyncConfig.id == config_id)
                .values(
                    webhook_url=webhook_url,
                    webhook_registered=True,
                    last_sync_at=datetime.utcnow(),
                )
            )
            await db.execute(stmt)
            await db.commit()

            logger.info(
                "webhook_registered",
                config_id=config_id,
                user_id=user_id,
                sheet_id=sheet_id,
                webhook_url=webhook_url,
            )

            return {
                "config_id": config_id,
                "webhook_url": webhook_url,
                "status": "registered",
                "mapping_result": mapping_result,
                "headers": headers,
            }

        except Exception as e:
            logger.error("register_webhook_failed", config_id=config_id, error=str(e))
            raise

    async def get_field_mappings(
        self, db: AsyncSession, config_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get all field mappings for a config
        
        Args:
            db: Database session
            config_id: SheetSyncConfig ID
            
        Returns:
            List of field mappings
        """
        try:
            stmt = select(FieldMapping).where(FieldMapping.config_id == config_id)
            result = await db.execute(stmt)
            mappings = result.scalars().all()

            mapping_list = [
                {
                    "id": m.id,
                    "sheet_column_index": m.sheet_column_index,
                    "sheet_column_name": m.sheet_column_name,
                    "bitrix_field": m.bitrix_field,
                    "data_type": m.data_type,
                    "is_updatable": m.is_updatable,
                }
                for m in mappings
            ]

            return mapping_list

        except Exception as e:
            logger.error("get_field_mappings_failed", config_id=config_id, error=str(e))
            raise

    async def update_field_mapping(
        self,
        db: AsyncSession,
        mapping_id: int,
        bitrix_field: str,
        is_updatable: bool = True,
    ) -> bool:
        """
        Update a field mapping (user correction)
        
        Args:
            db: Database session
            mapping_id: FieldMapping ID
            bitrix_field: New Bitrix24 field name
            is_updatable: Can this field be updated?
            
        Returns:
            Success status
        """
        try:
            stmt = (
                update(FieldMapping)
                .where(FieldMapping.id == mapping_id)
                .values(
                    bitrix_field=bitrix_field,
                    is_updatable=is_updatable,
                )
            )
            await db.execute(stmt)
            await db.commit()

            logger.info("field_mapping_updated", mapping_id=mapping_id)
            return True

        except Exception as e:
            logger.error("update_field_mapping_failed", mapping_id=mapping_id, error=str(e))
            await db.rollback()
            return False

    async def unregister_webhook(
        self, db: AsyncSession, config_id: int
    ) -> bool:
        """
        Unregister/disable webhook for a config
        
        Args:
            db: Database session
            config_id: SheetSyncConfig ID
            
        Returns:
            Success status
        """
        try:
            stmt = (
                update(SheetSyncConfig)
                .where(SheetSyncConfig.id == config_id)
                .values(
                    webhook_registered=False,
                    enabled=False,
                )
            )
            await db.execute(stmt)
            await db.commit()

            logger.info("webhook_unregistered", config_id=config_id)
            return True

        except Exception as e:
            logger.error("unregister_webhook_failed", config_id=config_id, error=str(e))
            await db.rollback()
            return False

    async def validate_webhook_payload(
        self,
        db: AsyncSession,
        config_id: int,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate webhook payload from Google Apps Script
        
        Expected payload format:
        {
            "sheet_id": "...",
            "gid": "0",
            "event": "row_edited",
            "row_id": 5,
            "old_values": {...},
            "new_values": {...}
        }
        
        Args:
            db: Database session
            config_id: SheetSyncConfig ID
            payload: Webhook payload
            
        Returns:
            Validated and processed payload
        """
        try:
            # Get config
            stmt = select(SheetSyncConfig).where(SheetSyncConfig.id == config_id)
            result = await db.execute(stmt)
            config = result.scalars().first()

            if not config:
                raise Exception(f"Config not found: {config_id}")

            # Validate payload structure
            required_fields = ["event", "row_id", "new_values"]
            for field in required_fields:
                if field not in payload:
                    raise Exception(f"Missing required field: {field}")

            # Get field mappings
            mappings = await self.get_field_mappings(db, config_id)
            mapping_dict = {m["sheet_column_index"]: m for m in mappings}

            # Extract changes (only mapped fields)
            changes = {}
            new_values = payload.get("new_values", {})
            old_values = payload.get("old_values", {})

            for col_idx, col_value in enumerate(new_values):
                if col_idx in mapping_dict:
                    mapping = mapping_dict[col_idx]
                    old_val = old_values.get(col_idx) if old_values else None

                    if col_value != old_val:  # Only if changed
                        changes[mapping["bitrix_field"]] = {
                            "old": old_val,
                            "new": col_value,
                        }

            logger.info(
                "webhook_payload_validated",
                config_id=config_id,
                event=payload.get("event"),
                row_id=payload.get("row_id"),
                changes_count=len(changes),
            )

            return {
                "is_valid": len(changes) > 0,
                "config_id": config_id,
                "event": payload.get("event"),
                "row_id": payload.get("row_id"),
                "changes": changes,
                "entity_type": config.entity_type,
            }

        except Exception as e:
            logger.error("webhook_payload_validation_failed", config_id=config_id, error=str(e))
            return {
                "is_valid": False,
                "error": str(e),
            }
