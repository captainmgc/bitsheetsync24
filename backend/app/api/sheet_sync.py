"""
Sheet Sync API Endpoints
Handles:
- OAuth callback processing
- Sync configuration management
- Webhook event processing
- Field mapping management
- Sync history queries
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.database import get_db
from app.services.google_sheets_auth import GoogleSheetsAuth
from app.services.sheets_webhook import SheetsWebhookManager
from app.services.change_processor import ChangeProcessor, SyncStatus
from app.services.bitrix_updater import Bitrix24Updater
from app.models.sheet_sync import SheetSyncConfig, FieldMapping, UserSheetsToken
from app.config import settings

import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/sheet-sync", tags=["sheet-sync"])


# ============================================================================
# CORS OPTIONS HANDLER
# ============================================================================

@router.options("/{rest_of_path:path}")
async def options_handler(rest_of_path: str):
    """Handle CORS preflight requests"""
    return {}


# ============================================================================
# OAUTH ENDPOINTS
# ============================================================================


@router.post("/oauth/start")
async def start_oauth(
    db: AsyncSession = Depends(get_db),
):
    """
    Generate Google OAuth URL for user
    
    Response:
    {
        "oauth_url": "https://accounts.google.com/o/oauth2/v2/auth?..."
    }
    """
    try:
        # Generate unique state for this session
        import uuid
        state = str(uuid.uuid4())

        # Get OAuth URL
        oauth_auth = GoogleSheetsAuth()
        oauth_url = oauth_auth.get_google_oauth_url(state)

        # TODO: Store state in session/cache for validation in callback
        # session.state = state  # or use Redis

        logger.info("oauth_start", state=state)

        return {
            "oauth_url": oauth_url,
            "state": state,
        }

    except Exception as e:
        logger.error("oauth_start_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/oauth/callback")
async def oauth_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Google OAuth callback
    
    Exchanges authorization code for tokens and stores in database
    
    Query params:
    - code: Authorization code from Google
    - state: State parameter for security
    
    Response:
    {
        "success": true,
        "user_id": "123456",
        "user_email": "user@gmail.com",
        "redirect_url": "http://localhost:3000/sheet-sync/config"
    }
    """
    try:
        if not code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing authorization code",
            )

        # TODO: Validate state from session

        # Exchange code for tokens
        oauth_auth = GoogleSheetsAuth()
        token_data = await oauth_auth.exchange_code_for_tokens(code)

        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange code for tokens",
            )

        # Extract user info (would come from token validation)
        # For now, we'll use the access token to get user info
        user_id = token_data.get("user_id", "unknown")
        user_email = token_data.get("email", "unknown")

        # Save tokens to database
        await oauth_auth.save_user_tokens(
            db=db,
            user_id=user_id,
            user_email=user_email,
            access_token=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token"),
            expires_in=token_data.get("expires_in"),
            scopes=token_data.get("scopes"),
        )

        logger.info(
            "oauth_callback_success",
            user_id=user_id,
            user_email=user_email,
        )

        return {
            "success": True,
            "user_id": user_id,
            "user_email": user_email,
            "redirect_url": f"{settings.frontend_url}/sheet-sync/config",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("oauth_callback_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/oauth/token")
async def get_user_token(
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Get existing user token if already authenticated
    
    Query params:
    - user_id: User ID
    
    Response:
    {
        "user_id": "123456",
        "user_email": "user@gmail.com",
        "is_active": true,
        "last_used_at": "2025-11-07T10:00:00"
    }
    """
    try:
        # Query for user token
        stmt = select(UserSheetsToken).where(UserSheetsToken.user_id == user_id)
        result = await db.execute(stmt)
        token_record = result.scalar_one_or_none()
        
        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No token found for user",
            )
        
        if not token_record.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token is inactive",
            )
        
        logger.info("get_user_token_success", user_id=user_id)
        
        return {
            "user_id": token_record.user_id,
            "user_email": token_record.user_email,
            "is_active": token_record.is_active,
            "last_used_at": token_record.last_used_at.isoformat() if token_record.last_used_at else None,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_user_token_failed", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/oauth/auto-connect")
async def auto_connect_oauth(
    user_id: str = Query(...),
    user_email: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Auto-connect user who is already authenticated via NextAuth/Google OAuth
    Creates a placeholder token record so user can proceed with sync configuration
    without clicking "Connect with Google" again
    
    This is called when user already has NextAuth session but no Sheet Sync token yet
    
    Query params:
    - user_id: User ID from NextAuth session
    - user_email: User email from NextAuth session
    
    Response:
    {
        "success": true,
        "user_id": "123456",
        "user_email": "user@gmail.com"
    }
    """
    try:
        if not user_id or not user_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing user_id or user_email",
            )

        # Check if token already exists
        stmt = select(UserSheetsToken).where(UserSheetsToken.user_id == user_id)
        result = await db.execute(stmt)
        existing_token = result.scalar_one_or_none()

        if existing_token:
            # Token already exists
            logger.info("auto_connect_token_exists", user_id=user_id)
            return {
                "success": True,
                "user_id": existing_token.user_id,
                "user_email": existing_token.user_email,
                "already_exists": True,
            }

        # Create a new token record with placeholder tokens
        # These will be replaced when user completes OAuth callback
        new_token = UserSheetsToken(
            user_id=user_id,
            user_email=user_email,
            access_token="",  # Will be set on first OAuth callback
            refresh_token="",  # Will be set on first OAuth callback
            token_expires_at=None,
            scopes=[],
            is_active=True,
        )
        
        db.add(new_token)
        await db.commit()

        logger.info("auto_connect_success", user_id=user_id, user_email=user_email)

        return {
            "success": True,
            "user_id": user_id,
            "user_email": user_email,
            "already_exists": False,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("auto_connect_failed", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# SYNC CONFIGURATION ENDPOINTS
# ============================================================================


@router.post("/config")
async def create_sync_config(
    config_data: Dict[str, Any],
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Create new sheet sync configuration
    
    Request body:
    {
        "sheet_id": "abc123...",
        "gid": "0",
        "sheet_name": "Leads",
        "entity_type": "contacts",
        "color_scheme": {"primary": "#1f2937", "secondary": "#374151"},
        "is_custom_view": false
    }
    
    Response:
    {
        "id": 1,
        "sheet_id": "abc123...",
        "webhook_url": "http://localhost:8000/api/v1/sheet-sync/webhook/1",
        "status": "registered"
    }
    """
    try:
        # Validate user has valid tokens
        oauth_auth = GoogleSheetsAuth()
        token = await oauth_auth.get_valid_token(db, user_id)

        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User tokens not found or expired",
            )

        # Create config in database
        config = SheetSyncConfig(
            user_id=user_id,
            sheet_id=config_data.get("sheet_id"),
            sheet_gid=config_data.get("gid", "0"),
            sheet_name=config_data.get("sheet_name"),
            entity_type=config_data.get("entity_type"),
            is_custom_view=config_data.get("is_custom_view", False),
            color_scheme=config_data.get("color_scheme", {}),
            enabled=False,  # Not enabled until webhook registered
        )
        db.add(config)
        await db.flush()

        config_id = config.id

        # Register webhook and auto-detect fields
        webhook_manager = SheetsWebhookManager(token)
        webhook_result = await webhook_manager.register_webhook(
            db=db,
            config_id=config_id,
            user_id=user_id,
            sheet_id=config_data.get("sheet_id"),
            gid=config_data.get("gid", "0"),
            entity_type=config_data.get("entity_type"),
        )

        # Enable config after successful webhook registration
        config.enabled = True
        await db.commit()

        logger.info(
            "sync_config_created",
            config_id=config_id,
            user_id=user_id,
            entity_type=config_data.get("entity_type"),
        )

        return {
            "id": config_id,
            "sheet_id": config_data.get("sheet_id"),
            "sheet_name": config_data.get("sheet_name"),
            "entity_type": config_data.get("entity_type"),
            "webhook_url": webhook_result.get("webhook_url"),
            "status": "registered",
            "mapping_result": webhook_result.get("mapping_result"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("create_sync_config_failed", user_id=user_id, error=str(e))
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/config/{config_id}")
async def get_sync_config(
    config_id: int,
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Get sync configuration details
    """
    try:
        from sqlalchemy import select

        # Get config
        stmt = select(SheetSyncConfig).where(SheetSyncConfig.id == config_id)
        result = await db.execute(stmt)
        config = result.scalars().first()

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Config not found: {config_id}",
            )

        # Verify ownership
        if config.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        # Get field mappings
        webhook_manager = SheetsWebhookManager("")  # Token not needed for reading mappings
        mappings = await webhook_manager.get_field_mappings(db, config_id)

        return {
            "id": config.id,
            "sheet_id": config.sheet_id,
            "sheet_name": config.sheet_name,
            "entity_type": config.entity_type,
            "webhook_url": config.webhook_url,
            "enabled": config.enabled,
            "color_scheme": config.color_scheme,
            "created_at": config.created_at.isoformat(),
            "last_sync_at": config.last_sync_at.isoformat() if config.last_sync_at else None,
            "field_mappings": mappings,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_sync_config_failed", config_id=config_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/config/{config_id}")
async def delete_sync_config(
    config_id: int,
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete sync configuration
    """
    try:
        from sqlalchemy import select

        # Get config
        stmt = select(SheetSyncConfig).where(SheetSyncConfig.id == config_id)
        result = await db.execute(stmt)
        config = result.scalars().first()

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Config not found: {config_id}",
            )

        # Verify ownership
        if config.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        # Delete config
        await db.delete(config)
        await db.commit()

        logger.info("sync_config_deleted", config_id=config_id, user_id=user_id)

        return {"status": "deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_sync_config_failed", config_id=config_id, error=str(e))
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# FIELD MAPPING ENDPOINTS
# ============================================================================


@router.post("/field-mapping/{mapping_id}")
async def update_field_mapping(
    mapping_id: int,
    config_id: int = Query(...),
    user_id: str = Query(...),
    bitrix_field: str = Query(...),
    is_updatable: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """
    Update field mapping (user correction)
    """
    try:
        from sqlalchemy import select

        # Verify config ownership
        stmt = select(SheetSyncConfig).where(SheetSyncConfig.id == config_id)
        result = await db.execute(stmt)
        config = result.scalars().first()

        if not config or config.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        # Update mapping
        webhook_manager = SheetsWebhookManager("")
        success = await webhook_manager.update_field_mapping(
            db=db,
            mapping_id=mapping_id,
            bitrix_field=bitrix_field,
            is_updatable=is_updatable,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update field mapping",
            )

        logger.info("field_mapping_updated", mapping_id=mapping_id)

        return {"success": True, "mapping_id": mapping_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_field_mapping_failed", mapping_id=mapping_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# WEBHOOK ENDPOINT
# ============================================================================


@router.post("/webhook/{config_id}")
async def webhook_received(
    config_id: int,
    webhook_payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    """
    Receive webhook event from Google Apps Script
    
    Expected payload:
    {
        "event": "row_updated",
        "row_id": 5,
        "entity_id": "123",
        "old_values": [...],
        "new_values": [...],
        "sheet_id": "abc...",
        "gid": "0"
    }
    """
    try:
        from sqlalchemy import select

        # Get config
        stmt = select(SheetSyncConfig).where(SheetSyncConfig.id == config_id)
        result = await db.execute(stmt)
        config = result.scalars().first()

        if not config:
            logger.warning("webhook_received_unknown_config", config_id=config_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Config not found",
            )

        if not config.enabled:
            logger.warning("webhook_received_disabled_config", config_id=config_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sync config is disabled",
            )

        # Validate webhook payload
        webhook_manager = SheetsWebhookManager("")
        validation_result = await webhook_manager.validate_webhook_payload(
            db=db,
            config_id=config_id,
            payload=webhook_payload,
        )

        if not validation_result["is_valid"]:
            logger.warning(
                "webhook_payload_invalid",
                config_id=config_id,
                error=validation_result.get("error"),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=validation_result.get("error", "Invalid payload"),
            )

        # Process webhook event
        processor = ChangeProcessor()
        process_result = await processor.process_webhook_event(
            db=db,
            config_id=config_id,
            user_id=config.user_id,
            webhook_data=validation_result,
        )

        # TODO: Queue for async processing to Bitrix24
        # For now, return immediately
        # In production, this should be queued to a task queue (Celery, RQ, etc)

        logger.info(
            "webhook_processed",
            config_id=config_id,
            event_id=process_result.get("event_id"),
            log_id=process_result.get("log_id"),
        )

        return {
            "status": "queued",
            "event_id": process_result.get("event_id"),
            "log_id": process_result.get("log_id"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("webhook_processing_failed", config_id=config_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# SYNC HISTORY & STATUS ENDPOINTS
# ============================================================================


@router.get("/logs/{config_id}")
async def get_sync_logs(
    config_id: int,
    user_id: str = Query(...),
    status_filter: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Get sync history for a configuration
    
    Query params:
    - status_filter: pending, syncing, completed, failed
    - limit: Max results (1-100)
    """
    try:
        from sqlalchemy import select

        # Verify config ownership
        stmt = select(SheetSyncConfig).where(SheetSyncConfig.id == config_id)
        result = await db.execute(stmt)
        config = result.scalars().first()

        if not config or config.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        # Get history
        processor = ChangeProcessor()
        status_enum = None
        if status_filter:
            try:
                status_enum = SyncStatus(status_filter)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status_filter}",
                )

        history = await processor.get_sync_history(
            db=db,
            config_id=config_id,
            status=status_enum,
            limit=limit,
        )

        return {
            "config_id": config_id,
            "total": len(history),
            "logs": history,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_sync_logs_failed", config_id=config_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/status/{log_id}")
async def get_update_status(
    log_id: int,
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Get status of a specific sync operation
    """
    try:
        from sqlalchemy import select

        # Get log and verify ownership
        from app.models.sheet_sync import ReverseSyncLog

        stmt = select(ReverseSyncLog).where(ReverseSyncLog.id == log_id)
        result = await db.execute(stmt)
        sync_log = result.scalars().first()

        if not sync_log or sync_log.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        # Get config for webhook URL
        stmt = select(SheetSyncConfig).where(SheetSyncConfig.id == sync_log.config_id)
        result = await db.execute(stmt)
        config = result.scalars().first()

        # Get status
        updater = Bitrix24Updater(config.webhook_url or "")
        status_info = await updater.get_update_status(db, log_id)

        return status_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_update_status_failed", log_id=log_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/retry/{config_id}")
async def retry_failed_syncs(
    config_id: int,
    user_id: str = Query(...),
    max_retries: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Retry failed sync operations for a configuration
    """
    try:
        from sqlalchemy import select

        # Verify config ownership
        stmt = select(SheetSyncConfig).where(SheetSyncConfig.id == config_id)
        result = await db.execute(stmt)
        config = result.scalars().first()

        if not config or config.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        # Retry failed syncs
        updater = Bitrix24Updater(config.webhook_url or "")
        retry_result = await updater.retry_failed_syncs(
            db=db,
            config_id=config_id,
            max_retries=max_retries,
        )

        logger.info("retry_failed_syncs_triggered", config_id=config_id)

        return retry_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("retry_failed_syncs_failed", config_id=config_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
