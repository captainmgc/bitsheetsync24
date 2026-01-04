"""
Bitrix24 Updater Service
Sends processed changes to Bitrix24 API
Handles:
- Bitrix24 batch API calls
- Error handling and retries
- Rate limiting
- API response validation
"""

import httpx
import json
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.sheet_sync import ReverseSyncLog
from app.services.change_processor import SyncStatus

logger = structlog.get_logger()


class Bitrix24Updater:
    """
    Manages Bitrix24 API updates via webhooks
    """

    def __init__(self, webhook_url: str):
        """
        Initialize with Bitrix24 webhook URL
        
        Args:
            webhook_url: Bitrix24 incoming webhook URL (from webhook_input)
        """
        self.webhook_url = webhook_url
        self.timeout = 30

    async def update_entity(
        self,
        entity_type: str,
        entity_id: str,
        fields: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Send single entity update to Bitrix24
        
        Args:
            entity_type: Entity type (deals, contacts, companies, tasks)
            entity_id: Bitrix24 entity ID
            fields: Fields to update
            
        Returns:
            Bitrix24 API response
        """
        try:
            payload = {
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "fields": fields,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    timeout=self.timeout,
                    headers={"Content-Type": "application/json"},
                )

                response_data = response.json() if response.text else {}

                if response.status_code == 200 or response.status_code == 201:
                    logger.info(
                        "bitrix24_update_success",
                        entity_type=entity_type,
                        entity_id=entity_id,
                        fields_count=len(fields),
                        status_code=response.status_code,
                    )
                    return {
                        "success": True,
                        "status_code": response.status_code,
                        "response": response_data,
                    }
                else:
                    logger.warning(
                        "bitrix24_update_failed",
                        entity_type=entity_type,
                        entity_id=entity_id,
                        status_code=response.status_code,
                        response=response_data,
                    )
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "error": response_data.get("error", "Unknown error"),
                        "response": response_data,
                    }

        except httpx.TimeoutException:
            error_msg = f"Bitrix24 update timeout for {entity_type}:{entity_id}"
            logger.error("bitrix24_update_timeout", entity_type=entity_type, entity_id=entity_id)
            return {"success": False, "error": error_msg}

        except httpx.HTTPError as e:
            error_msg = f"Bitrix24 HTTP error: {str(e)}"
            logger.error(
                "bitrix24_update_http_error",
                entity_type=entity_type,
                entity_id=entity_id,
                error=str(e),
            )
            return {"success": False, "error": error_msg}

        except Exception as e:
            error_msg = f"Bitrix24 update error: {str(e)}"
            logger.error(
                "bitrix24_update_error",
                entity_type=entity_type,
                entity_id=entity_id,
                error=str(e),
            )
            return {"success": False, "error": error_msg}

    async def process_sync_log(
        self,
        db: AsyncSession,
        log_id: int,
        bitrix_update: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Process and send sync log update to Bitrix24
        
        Args:
            db: Database session
            log_id: ReverseSyncLog ID
            bitrix_update: Update data from ChangeProcessor
            
        Returns:
            Processing result
        """
        try:
            # Get sync log
            stmt = select(ReverseSyncLog).where(ReverseSyncLog.id == log_id)
            result = await db.execute(stmt)
            sync_log = result.scalars().first()

            if not sync_log:
                return {"success": False, "error": f"Sync log not found: {log_id}"}

            # Mark as syncing
            stmt = (
                update(ReverseSyncLog)
                .where(ReverseSyncLog.id == log_id)
                .values(status=SyncStatus.SYNCING.value)
            )
            await db.execute(stmt)
            await db.commit()

            # Send to Bitrix24
            result = await self.update_entity(
                entity_type=bitrix_update["entity_type"],
                entity_id=bitrix_update["entity_id"],
                fields=bitrix_update["fields"],
            )

            # Update sync log with result
            if result["success"]:
                status = SyncStatus.COMPLETED.value
                error_msg = None
            else:
                status = SyncStatus.FAILED.value
                error_msg = result.get("error")

            stmt = (
                update(ReverseSyncLog)
                .where(ReverseSyncLog.id == log_id)
                .values(
                    status=status,
                    error_message=error_msg,
                    updated_at=datetime.utcnow(),
                )
            )
            await db.execute(stmt)
            await db.commit()

            logger.info(
                "sync_log_processed",
                log_id=log_id,
                status=status,
                entity_type=bitrix_update["entity_type"],
            )

            return {
                "log_id": log_id,
                "status": status,
                "bitrix_response": result,
            }

        except Exception as e:
            logger.error("process_sync_log_failed", log_id=log_id, error=str(e))

            # Mark as failed
            stmt = (
                update(ReverseSyncLog)
                .where(ReverseSyncLog.id == log_id)
                .values(
                    status=SyncStatus.FAILED.value,
                    error_message=str(e),
                )
            )
            await db.execute(stmt)
            await db.commit()

            return {"success": False, "error": str(e)}

    async def batch_process_syncs(
        self,
        db: AsyncSession,
        sync_updates: List[Dict[str, Any]],
        concurrent_limit: int = 5,
    ) -> Dict[str, Any]:
        """
        Process multiple syncs concurrently
        
        Args:
            db: Database session
            sync_updates: List of sync updates with log_id and bitrix_update
            concurrent_limit: Max concurrent requests
            
        Returns:
            Batch processing result
        """
        try:
            results = {
                "total": len(sync_updates),
                "successful": 0,
                "failed": 0,
                "details": [],
            }

            # Process in batches to avoid overwhelming the server
            for i in range(0, len(sync_updates), concurrent_limit):
                batch = sync_updates[i : i + concurrent_limit]

                # Create tasks for batch
                tasks = [
                    self.process_sync_log(db, update["log_id"], update["bitrix_update"])
                    for update in batch
                ]

                # Run concurrently
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in batch_results:
                    if isinstance(result, Exception):
                        results["failed"] += 1
                        results["details"].append({"error": str(result)})
                    elif result.get("status") == SyncStatus.COMPLETED.value:
                        results["successful"] += 1
                        results["details"].append({
                            "log_id": result.get("log_id"),
                            "status": "completed",
                        })
                    else:
                        results["failed"] += 1
                        results["details"].append({
                            "log_id": result.get("log_id"),
                            "error": result.get("error"),
                        })

                # Add delay between batches (rate limiting)
                if i + concurrent_limit < len(sync_updates):
                    await asyncio.sleep(1)

            logger.info(
                "batch_syncs_completed",
                total=results["total"],
                successful=results["successful"],
                failed=results["failed"],
            )

            return results

        except Exception as e:
            logger.error("batch_process_syncs_failed", error=str(e))
            return {
                "total": len(sync_updates),
                "successful": 0,
                "failed": len(sync_updates),
                "error": str(e),
            }

    async def get_update_status(
        self,
        db: AsyncSession,
        log_id: int,
    ) -> Dict[str, Any]:
        """
        Get status of a specific update
        
        Args:
            db: Database session
            log_id: ReverseSyncLog ID
            
        Returns:
            Update status information
        """
        try:
            stmt = select(ReverseSyncLog).where(ReverseSyncLog.id == log_id)
            result = await db.execute(stmt)
            sync_log = result.scalars().first()

            if not sync_log:
                return {"error": f"Sync log not found: {log_id}"}

            return {
                "id": sync_log.id,
                "entity_id": sync_log.entity_id,
                "row_id": sync_log.sheet_row_id,
                "status": sync_log.status,
                "changes": sync_log.changed_fields,
                "error": sync_log.error_message,
                "created_at": sync_log.created_at.isoformat(),
                "updated_at": sync_log.updated_at.isoformat() if sync_log.updated_at else None,
            }

        except Exception as e:
            logger.error("get_update_status_failed", log_id=log_id, error=str(e))
            return {"error": str(e)}

    async def retry_failed_syncs(
        self,
        db: AsyncSession,
        config_id: int,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Retry failed sync operations
        
        Args:
            db: Database session
            config_id: SheetSyncConfig ID
            max_retries: Maximum retry count
            
        Returns:
            Retry result
        """
        try:
            # Get failed syncs
            stmt = (
                select(ReverseSyncLog)
                .where(ReverseSyncLog.config_id == config_id)
                .where(ReverseSyncLog.status == SyncStatus.FAILED.value)
                .order_by(ReverseSyncLog.created_at)
                .limit(max_retries)
            )

            result = await db.execute(stmt)
            failed_logs = result.scalars().all()

            if not failed_logs:
                return {"retried": 0, "message": "No failed syncs to retry"}

            # Mark as retrying
            for log in failed_logs:
                stmt = (
                    update(ReverseSyncLog)
                    .where(ReverseSyncLog.id == log.id)
                    .values(status=SyncStatus.RETRYING.value)
                )
                await db.execute(stmt)

            await db.commit()

            logger.info("failed_syncs_marked_for_retry", config_id=config_id, count=len(failed_logs))

            return {
                "retried": len(failed_logs),
                "message": f"{len(failed_logs)} failed syncs marked for retry",
            }

        except Exception as e:
            logger.error("retry_failed_syncs_failed", config_id=config_id, error=str(e))
            return {"error": str(e)}
