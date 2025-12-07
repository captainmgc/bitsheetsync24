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
from app.services.bitrix_field_detector import Bitrix24FieldDetector, get_bitrix_field_detector
from app.services.sheet_formatter import SheetFormatter
from app.services.apps_script_installer import AppsScriptInstaller
from app.models.sheet_sync import SheetSyncConfig, FieldMapping, UserSheetsToken, SheetRowTimestamp
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


# ============================================================================
# BITRIX24 FIELD DETECTION ENDPOINTS
# ============================================================================


@router.get("/bitrix-fields/{entity_type}")
async def get_bitrix_fields(
    entity_type: str,
    editable_only: bool = Query(False),
):
    """
    Get Bitrix24 fields for an entity type
    
    Path params:
    - entity_type: leads, contacts, companies, deals, tasks, activities
    
    Query params:
    - editable_only: If true, only return editable fields
    
    Response:
    {
        "entity_type": "deals",
        "total_fields": 45,
        "editable_count": 32,
        "readonly_count": 13,
        "fields": {...}
    }
    """
    try:
        detector = get_bitrix_field_detector()
        
        if editable_only:
            fields = await detector.get_editable_fields(entity_type)
        else:
            fields = await detector.fetch_entity_fields(entity_type)
        
        editable_fields = await detector.get_editable_fields(entity_type)
        readonly_fields = await detector.get_readonly_fields(entity_type)
        
        return {
            "entity_type": entity_type,
            "total_fields": len(fields),
            "editable_count": len(editable_fields),
            "readonly_count": len(readonly_fields),
            "fields": fields,
            "editable_fields": list(editable_fields.keys()),
            "readonly_fields": list(readonly_fields.keys()),
        }
        
    except Exception as e:
        logger.error("get_bitrix_fields_failed", entity_type=entity_type, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/bitrix-fields")
async def get_all_bitrix_fields_summary():
    """
    Get summary of all entity fields
    
    Response:
    {
        "leads": {"total": 45, "editable": 32, "readonly": 13},
        "contacts": {"total": 50, "editable": 40, "readonly": 10},
        ...
    }
    """
    try:
        detector = get_bitrix_field_detector()
        summary = await detector.get_all_entity_fields_summary()
        
        return {
            "summary": summary,
            "supported_entities": list(detector.ENTITY_FIELD_METHODS.keys()),
        }
        
    except Exception as e:
        logger.error("get_all_bitrix_fields_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/classify-columns")
async def classify_sheet_columns(
    data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    """
    Classify sheet columns as editable or read-only based on Bitrix24 field permissions
    
    Request body:
    {
        "entity_type": "deals",
        "sheet_headers": ["ID", "TITLE", "OPPORTUNITY", "DATE_CREATE", ...],
        "field_mappings": {"TITLE": "TITLE", "Ad": "NAME", ...}
    }
    
    Response:
    {
        "editable_columns": [{"index": 1, "header": "TITLE", ...}],
        "readonly_columns": [{"index": 0, "header": "ID", ...}]
    }
    """
    try:
        entity_type = data.get("entity_type")
        sheet_headers = data.get("sheet_headers", [])
        field_mappings = data.get("field_mappings", {})
        
        if not entity_type or not sheet_headers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="entity_type and sheet_headers are required",
            )
        
        detector = get_bitrix_field_detector()
        editable_cols, readonly_cols = await detector.classify_sheet_columns(
            entity_type,
            sheet_headers,
            field_mappings
        )
        
        return {
            "entity_type": entity_type,
            "total_columns": len(sheet_headers),
            "editable_columns": editable_cols,
            "readonly_columns": readonly_cols,
            "editable_count": len(editable_cols),
            "readonly_count": len(readonly_cols),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("classify_columns_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# SHEET FORMATTING ENDPOINTS
# ============================================================================


@router.post("/format-sheet/{config_id}")
async def format_sheet_for_sync(
    config_id: int,
    user_id: str = Query(...),
    add_status_column: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """
    Format Google Sheet with colors and sync status column
    - Editable columns: Light green header
    - Read-only columns: Light red header
    - Adds "Senkronizasyon" status column
    
    Query params:
    - user_id: User ID
    - add_status_column: Whether to add status column (default: true)
    
    Response:
    {
        "success": true,
        "status_column_index": 15,
        "editable_columns": 12,
        "readonly_columns": 3
    }
    """
    try:
        # Get config
        stmt = select(SheetSyncConfig).where(SheetSyncConfig.id == config_id)
        result = await db.execute(stmt)
        config = result.scalars().first()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Config not found",
            )
        
        if config.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        
        # Get user token
        oauth_auth = GoogleSheetsAuth()
        token = await oauth_auth.get_valid_token(db, user_id)
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User tokens not found or expired",
            )
        
        # Get field mappings for this config
        stmt = select(FieldMapping).where(FieldMapping.config_id == config_id)
        result = await db.execute(stmt)
        mappings = result.scalars().all()
        
        # Classify columns
        editable_indices = []
        readonly_indices = []
        
        for mapping in mappings:
            if mapping.is_updatable and not mapping.is_readonly:
                editable_indices.append(mapping.sheet_column_index)
            else:
                readonly_indices.append(mapping.sheet_column_index)
        
        # If no classification yet, use Bitrix24 field detector
        if not editable_indices and not readonly_indices:
            detector = get_bitrix_field_detector()
            headers = [m.sheet_column_name for m in mappings]
            field_map = {m.sheet_column_name: m.bitrix_field for m in mappings}
            
            editable_cols, readonly_cols = await detector.classify_sheet_columns(
                config.entity_type,
                headers,
                field_map
            )
            
            editable_indices = [c["index"] for c in editable_cols]
            readonly_indices = [c["index"] for c in readonly_cols]
            
            # Update field mappings with readonly info
            for mapping in mappings:
                is_readonly = mapping.sheet_column_index in readonly_indices
                mapping.is_readonly = is_readonly
                mapping.is_updatable = not is_readonly
                mapping.color_code = "#FFEBEE" if is_readonly else "#E8F5E9"
            
            await db.commit()
        
        # Format the sheet
        formatter = SheetFormatter(token)
        format_result = await formatter.format_sheet_for_reverse_sync(
            spreadsheet_id=config.sheet_id,
            gid=config.sheet_gid,
            editable_column_indices=editable_indices,
            readonly_column_indices=readonly_indices,
            add_status_column=add_status_column,
        )
        
        # Update config with status column index
        if format_result.get("success") and "status_column_index" in format_result:
            config.status_column_index = format_result["status_column_index"]
            await db.commit()
        
        logger.info(
            "sheet_formatted",
            config_id=config_id,
            editable=len(editable_indices),
            readonly=len(readonly_indices)
        )
        
        return format_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("format_sheet_failed", config_id=config_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/update-row-status/{config_id}")
async def update_row_sync_status(
    config_id: int,
    user_id: str = Query(...),
    row_number: int = Query(...),
    status: str = Query(...),
    error_message: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Update sync status for a specific row in the sheet
    
    Query params:
    - row_number: Row number (1-indexed)
    - status: synced, pending, error, conflict
    - error_message: Optional error message for error status
    """
    try:
        # Get config
        stmt = select(SheetSyncConfig).where(SheetSyncConfig.id == config_id)
        result = await db.execute(stmt)
        config = result.scalars().first()
        
        if not config or config.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        
        if not config.status_column_index:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status column not configured. Format the sheet first.",
            )
        
        # Get user token
        oauth_auth = GoogleSheetsAuth()
        token = await oauth_auth.get_valid_token(db, user_id)
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User tokens not found or expired",
            )
        
        # Update status in sheet
        formatter = SheetFormatter(token)
        update_result = await formatter.update_sync_status(
            spreadsheet_id=config.sheet_id,
            sheet_name=config.sheet_name or "Sheet1",
            row_number=row_number,
            status_column_index=config.status_column_index,
            status=status,
            error_message=error_message,
        )
        
        return update_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_row_status_failed", config_id=config_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# APPS SCRIPT INSTALLATION ENDPOINTS
# ============================================================================


@router.post("/install-webhook/{config_id}")
async def install_apps_script_webhook(
    config_id: int,
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Automatically install Google Apps Script webhook to user's sheet
    
    This creates an Apps Script project bound to the spreadsheet,
    adds webhook code, and sets up the onEdit trigger.
    
    Response:
    {
        "success": true,
        "script_id": "abc123...",
        "webhook_url": "https://etablo.japonkonutlari.com/api/v1/sheet-sync/webhook",
        "steps": [...]
    }
    """
    try:
        # Get config
        stmt = select(SheetSyncConfig).where(SheetSyncConfig.id == config_id)
        result = await db.execute(stmt)
        config = result.scalars().first()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Config not found",
            )
        
        if config.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        
        # Get user token
        oauth_auth = GoogleSheetsAuth()
        token = await oauth_auth.get_valid_token(db, user_id)
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User tokens not found or expired",
            )
        
        # Check if already installed
        if config.script_id:
            return {
                "success": True,
                "already_installed": True,
                "script_id": config.script_id,
                "message": "Webhook already installed",
            }
        
        # Install webhook
        installer = AppsScriptInstaller(token)
        install_result = await installer.install_webhook(
            spreadsheet_id=config.sheet_id,
            config_id=str(config_id),
            user_id=user_id,
            entity_type=config.entity_type,
        )
        
        # Update config with script info
        if install_result.get("success"):
            from datetime import datetime
            config.script_id = install_result.get("script_id")
            config.script_installed_at = datetime.utcnow()
            config.webhook_registered = True
            await db.commit()
        
        logger.info(
            "webhook_installed",
            config_id=config_id,
            script_id=install_result.get("script_id")
        )
        
        return install_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("install_webhook_failed", config_id=config_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/uninstall-webhook/{config_id}")
async def uninstall_apps_script_webhook(
    config_id: int,
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove Apps Script webhook from user's sheet
    """
    try:
        # Get config
        stmt = select(SheetSyncConfig).where(SheetSyncConfig.id == config_id)
        result = await db.execute(stmt)
        config = result.scalars().first()
        
        if not config or config.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        
        if not config.script_id:
            return {
                "success": True,
                "message": "No webhook installed",
            }
        
        # Get user token
        oauth_auth = GoogleSheetsAuth()
        token = await oauth_auth.get_valid_token(db, user_id)
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User tokens not found or expired",
            )
        
        # Uninstall webhook
        installer = AppsScriptInstaller(token)
        uninstall_result = await installer.uninstall_webhook(config.script_id)
        
        # Update config
        if uninstall_result.get("success"):
            config.script_id = None
            config.script_installed_at = None
            config.webhook_registered = False
            await db.commit()
        
        return uninstall_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("uninstall_webhook_failed", config_id=config_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# WEBHOOK RECEIVER (from Google Apps Script)
# ============================================================================


@router.post("/webhook")
async def receive_webhook_from_apps_script(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    """
    Receive webhook events from Google Apps Script
    
    This is the main endpoint that Apps Script sends changes to.
    
    Expected payload:
    {
        "event": "row_edited",
        "config_id": "123",
        "user_id": "user@gmail.com",
        "entity_type": "deals",
        "entity_id": "456",
        "row_number": 5,
        "changes": {
            "TITLE": {"old_value": "Old", "new_value": "New", "column_index": 1}
        },
        "row_data": {"ID": "456", "TITLE": "New", ...},
        "timestamp": "2025-11-27T10:30:00Z"
    }
    """
    try:
        # Validate required fields
        config_id = payload.get("config_id")
        if not config_id:
            return {"success": False, "error": "Missing config_id"}
        
        # Handle test events
        if payload.get("event") == "test":
            logger.info("webhook_test_received", config_id=config_id)
            return {"success": True, "message": "Test webhook received"}
        
        # Get config
        stmt = select(SheetSyncConfig).where(SheetSyncConfig.id == int(config_id))
        result = await db.execute(stmt)
        config = result.scalars().first()
        
        if not config:
            return {"success": False, "error": f"Config not found: {config_id}"}
        
        if not config.enabled:
            return {"success": False, "error": "Sync config is disabled"}
        
        # Extract entity info
        entity_id = payload.get("entity_id")
        entity_type = payload.get("entity_type", config.entity_type)
        row_number = payload.get("row_number")
        changes = payload.get("changes", {})
        row_data = payload.get("row_data", {})
        
        if not entity_id:
            return {"success": False, "error": "Missing entity_id (ID column)"}
        
        if not changes:
            return {"success": False, "error": "No changes detected"}
        
        # Check for conflicts (timestamp comparison)
        from datetime import datetime
        sheet_timestamp = datetime.fromisoformat(payload.get("timestamp", datetime.utcnow().isoformat()).replace("Z", "+00:00"))
        
        # Get or create row timestamp record
        stmt = select(SheetRowTimestamp).where(
            SheetRowTimestamp.config_id == config.id,
            SheetRowTimestamp.sheet_row_number == row_number
        )
        result = await db.execute(stmt)
        row_ts = result.scalars().first()
        
        conflict_detected = False
        if row_ts and row_ts.bitrix_modified_at and row_ts.last_sync_at:
            # Check if Bitrix was modified after last sync
            if row_ts.bitrix_modified_at > row_ts.last_sync_at:
                # Both sides modified - conflict!
                conflict_detected = True
                logger.warning(
                    "conflict_detected",
                    config_id=config_id,
                    row=row_number,
                    entity_id=entity_id
                )
        
        # Process the webhook event
        processor = ChangeProcessor()
        process_result = await processor.process_webhook_event(
            db=db,
            config_id=int(config_id),
            user_id=config.user_id,
            webhook_data={
                "event": payload.get("event"),
                "entity_id": entity_id,
                "row_number": row_number,
                "changes": changes,
                "row_data": row_data,
                "conflict_detected": conflict_detected,
            },
        )
        
        # If no conflict, proceed with Bitrix24 update
        if not conflict_detected and process_result.get("bitrix_update"):
            updater = Bitrix24Updater(settings.bitrix24_webhook_url)
            
            bitrix_update = process_result["bitrix_update"]
            update_result = await updater.update_entity(
                entity_type=entity_type,
                entity_id=str(entity_id),
                fields=bitrix_update.get("fields", {}),
            )
            
            # Update row timestamp
            if not row_ts:
                row_ts = SheetRowTimestamp(
                    config_id=config.id,
                    sheet_row_number=row_number,
                    entity_id=str(entity_id),
                )
                db.add(row_ts)
            
            row_ts.sheet_modified_at = sheet_timestamp
            row_ts.last_sync_at = datetime.utcnow()
            row_ts.last_sheet_values = row_data
            row_ts.sync_status = "synced" if update_result.get("success") else "error"
            
            await db.commit()
            
            if update_result.get("success"):
                logger.info(
                    "reverse_sync_completed",
                    config_id=config_id,
                    entity_id=entity_id,
                    fields_updated=len(changes)
                )
                return {
                    "success": True,
                    "message": "Bitrix24 updated successfully",
                    "entity_id": entity_id,
                    "fields_updated": list(changes.keys()),
                }
            else:
                return {
                    "success": False,
                    "error": update_result.get("error", "Bitrix24 update failed"),
                }
        
        elif conflict_detected:
            # Handle conflict - timestamp comparison, latest wins
            # For now, we'll let the sheet value win since user explicitly edited it
            logger.info(
                "conflict_resolved_sheet_wins",
                config_id=config_id,
                entity_id=entity_id
            )
            
            # Still update Bitrix (sheet wins)
            updater = Bitrix24Updater(settings.bitrix24_webhook_url)
            bitrix_update = process_result.get("bitrix_update", {})
            
            if bitrix_update:
                update_result = await updater.update_entity(
                    entity_type=entity_type,
                    entity_id=str(entity_id),
                    fields=bitrix_update.get("fields", {}),
                )
                
                return {
                    "success": update_result.get("success", False),
                    "message": "Conflict resolved (sheet wins)",
                    "conflict_detected": True,
                }
        
        return {
            "success": True,
            "message": "Event processed",
            "log_id": process_result.get("log_id"),
        }
        
    except Exception as e:
        logger.error("webhook_processing_error", error=str(e))
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================================
# ONE-CLICK SETUP ENDPOINT
# ============================================================================


@router.post("/setup-reverse-sync/{config_id}")
async def setup_reverse_sync(
    config_id: int,
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    One-click setup for reverse sync:
    1. Detect editable fields from Bitrix24
    2. Classify sheet columns
    3. Apply colors to sheet
    4. Add status column
    5. Install Apps Script webhook
    
    Response:
    {
        "success": true,
        "steps_completed": ["field_detection", "column_classification", "formatting", "webhook_install"],
        "editable_fields": 12,
        "readonly_fields": 3,
        "script_id": "abc123..."
    }
    """
    try:
        steps_completed = []
        result = {
            "config_id": config_id,
            "success": False,
        }
        
        # Get config
        stmt = select(SheetSyncConfig).where(SheetSyncConfig.id == config_id)
        db_result = await db.execute(stmt)
        config = db_result.scalars().first()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Config not found",
            )
        
        if config.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        
        # Get user token
        oauth_auth = GoogleSheetsAuth()
        token = await oauth_auth.get_valid_token(db, user_id)
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User tokens not found or expired",
            )
        
        # Step 1: Detect editable fields from Bitrix24
        detector = get_bitrix_field_detector()
        editable_fields = await detector.get_editable_fields(config.entity_type)
        readonly_fields = await detector.get_readonly_fields(config.entity_type)
        steps_completed.append("field_detection")
        result["editable_fields_count"] = len(editable_fields)
        result["readonly_fields_count"] = len(readonly_fields)
        
        # Step 2: Get sheet headers and classify columns
        webhook_manager = SheetsWebhookManager(token)
        headers = await webhook_manager.get_sheet_headers(config.sheet_id, config.sheet_gid)
        
        # Create field mappings
        field_mappings = {}
        for header in headers:
            # Try to match header to Bitrix field
            normalized = header.strip().upper().replace(" ", "_")
            if normalized in editable_fields or normalized in readonly_fields:
                field_mappings[header] = normalized
            else:
                field_mappings[header] = header.upper()
        
        editable_cols, readonly_cols = await detector.classify_sheet_columns(
            config.entity_type,
            headers,
            field_mappings
        )
        steps_completed.append("column_classification")
        
        # Step 3: Update field mappings in database
        # First delete existing mappings
        from sqlalchemy import delete
        await db.execute(delete(FieldMapping).where(FieldMapping.config_id == config_id))
        
        # Create new mappings
        for idx, header in enumerate(headers):
            bitrix_field = field_mappings.get(header, header.upper())
            is_editable = idx in [c["index"] for c in editable_cols]
            
            mapping = FieldMapping(
                config_id=config_id,
                sheet_column_index=idx,
                sheet_column_name=header,
                bitrix_field=bitrix_field,
                is_updatable=is_editable,
                is_readonly=not is_editable,
                color_code="#E8F5E9" if is_editable else "#FFEBEE",
                bitrix_field_type=editable_fields.get(bitrix_field, {}).get("type") if is_editable else None,
                bitrix_field_title=editable_fields.get(bitrix_field, {}).get("title") if is_editable else None,
            )
            db.add(mapping)
        
        await db.flush()
        steps_completed.append("mapping_saved")
        
        # Step 4: Format sheet with colors and add status column
        formatter = SheetFormatter(token)
        format_result = await formatter.format_sheet_for_reverse_sync(
            spreadsheet_id=config.sheet_id,
            gid=config.sheet_gid,
            editable_column_indices=[c["index"] for c in editable_cols],
            readonly_column_indices=[c["index"] for c in readonly_cols],
            add_status_column=True,
        )
        
        if format_result.get("success"):
            config.status_column_index = format_result.get("status_column_index")
            steps_completed.append("sheet_formatted")
        
        # Step 5: Install Apps Script webhook
        installer = AppsScriptInstaller(token)
        install_result = await installer.install_webhook(
            spreadsheet_id=config.sheet_id,
            config_id=str(config_id),
            user_id=user_id,
            entity_type=config.entity_type,
        )
        
        if install_result.get("success"):
            from datetime import datetime
            config.script_id = install_result.get("script_id")
            config.script_installed_at = datetime.utcnow()
            config.webhook_registered = True
            config.enabled = True
            steps_completed.append("webhook_installed")
            result["script_id"] = install_result.get("script_id")
        
        await db.commit()
        
        result["success"] = True
        result["steps_completed"] = steps_completed
        result["editable_columns"] = len(editable_cols)
        result["readonly_columns"] = len(readonly_cols)
        result["status_column_index"] = config.status_column_index
        
        logger.info(
            "reverse_sync_setup_completed",
            config_id=config_id,
            steps=steps_completed
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("setup_reverse_sync_failed", config_id=config_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# CHANGE DETECTION ENDPOINTS
# ============================================================================


@router.get("/changes/detect/{config_id}")
async def detect_sheet_changes(
    config_id: int,
    user_id: str = Query(...),
    row_limit: int = Query(None, description="Limit rows to check (for large sheets)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Detect changes in Google Sheet compared to last synced data
    
    Path params:
    - config_id: Sync configuration ID
    
    Query params:
    - user_id: User ID
    - row_limit: Optional limit on rows to check
    
    Response:
    {
        "config_id": 1,
        "sheet_id": "abc123",
        "detected_at": "2025-11-29T10:00:00",
        "has_changes": true,
        "total_rows_scanned": 100,
        "total_changed_rows": 5,
        "total_changed_cells": 12,
        "headers": ["ID", "Name", "Email", ...],
        "row_changes": [
            {
                "row_number": 2,
                "entity_id": "123",
                "change_type": "modified",
                "cell_changes": [
                    {
                        "row": 2,
                        "column": 1,
                        "column_name": "Name",
                        "old_value": "John",
                        "new_value": "John Doe",
                        "change_type": "modified",
                        "bitrix_field": "TITLE",
                        "is_editable": true
                    }
                ],
                "total_changes": 1,
                "editable_changes": 1
            }
        ]
    }
    """
    from app.services.change_detector import ChangeDetector
    
    try:
        # Get user token
        stmt = select(UserSheetsToken).where(UserSheetsToken.user_id == user_id)
        result = await db.execute(stmt)
        token_record = result.scalar_one_or_none()
        
        if not token_record or not token_record.access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google Sheets bağlantısı bulunamadı",
            )
        
        # Get valid token
        oauth_auth = GoogleSheetsAuth()
        token = await oauth_auth.get_valid_access_token(db, user_id)
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token yenileme başarısız",
            )
        
        # Detect changes
        detector = ChangeDetector(token)
        
        try:
            result = await detector.detect_changes(
                db=db,
                config_id=config_id,
                row_limit=row_limit,
            )
            
            return result.to_dict()
            
        finally:
            await detector.close()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("detect_changes_failed", config_id=config_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/changes/row/{config_id}/{row_number}")
async def get_row_change_details(
    config_id: int,
    row_number: int,
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed comparison for a specific row
    
    Path params:
    - config_id: Sync configuration ID
    - row_number: Row number to get details for
    
    Query params:
    - user_id: User ID
    
    Response:
    {
        "row_number": 2,
        "entity_id": "123",
        "last_sync_at": "2025-11-29T10:00:00",
        "comparison": [
            {
                "column": 0,
                "column_name": "ID",
                "current_value": "123",
                "stored_value": "123",
                "is_changed": false
            },
            {
                "column": 1,
                "column_name": "Name",
                "current_value": "John Doe",
                "stored_value": "John",
                "is_changed": true
            }
        ]
    }
    """
    from app.services.change_detector import ChangeDetector
    
    try:
        # Get user token
        stmt = select(UserSheetsToken).where(UserSheetsToken.user_id == user_id)
        result = await db.execute(stmt)
        token_record = result.scalar_one_or_none()
        
        if not token_record or not token_record.access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google Sheets bağlantısı bulunamadı",
            )
        
        # Get valid token
        oauth_auth = GoogleSheetsAuth()
        token = await oauth_auth.get_valid_access_token(db, user_id)
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token yenileme başarısız",
            )
        
        # Get row details
        detector = ChangeDetector(token)
        
        try:
            result = await detector.get_row_details(
                db=db,
                config_id=config_id,
                row_number=row_number,
            )
            
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Satır bulunamadı",
                )
            
            return result
            
        finally:
            await detector.close()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_row_details_failed", config_id=config_id, row=row_number, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/changes/snapshot/{config_id}")
async def save_sheet_snapshot(
    config_id: int,
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Save current sheet state as snapshot for future change detection
    
    Path params:
    - config_id: Sync configuration ID
    
    Query params:
    - user_id: User ID
    
    Response:
    {
        "success": true,
        "config_id": 1,
        "message": "Anlık görüntü kaydedildi"
    }
    """
    from app.services.change_detector import ChangeDetector
    
    try:
        # Get user token
        stmt = select(UserSheetsToken).where(UserSheetsToken.user_id == user_id)
        result = await db.execute(stmt)
        token_record = result.scalar_one_or_none()
        
        if not token_record or not token_record.access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google Sheets bağlantısı bulunamadı",
            )
        
        # Get valid token
        oauth_auth = GoogleSheetsAuth()
        token = await oauth_auth.get_valid_access_token(db, user_id)
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token yenileme başarısız",
            )
        
        # Save snapshot
        detector = ChangeDetector(token)
        
        try:
            success = await detector.save_snapshot(
                db=db,
                config_id=config_id,
            )
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Anlık görüntü kaydedilemedi",
                )
            
            return {
                "success": True,
                "config_id": config_id,
                "message": "Anlık görüntü kaydedildi",
            }
            
        finally:
            await detector.close()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("save_snapshot_failed", config_id=config_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/changes/summary/{config_id}")
async def get_changes_summary(
    config_id: int,
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a quick summary of changes without full details
    
    Path params:
    - config_id: Sync configuration ID
    
    Query params:
    - user_id: User ID
    
    Response:
    {
        "config_id": 1,
        "has_changes": true,
        "total_changed_rows": 5,
        "total_changed_cells": 12,
        "editable_changes": 8,
        "readonly_changes": 4,
        "last_check_at": "2025-11-29T10:00:00"
    }
    """
    from app.services.change_detector import ChangeDetector
    
    try:
        # Get user token
        stmt = select(UserSheetsToken).where(UserSheetsToken.user_id == user_id)
        result = await db.execute(stmt)
        token_record = result.scalar_one_or_none()
        
        if not token_record or not token_record.access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google Sheets bağlantısı bulunamadı",
            )
        
        # Get valid token
        oauth_auth = GoogleSheetsAuth()
        token = await oauth_auth.get_valid_access_token(db, user_id)
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token yenileme başarısız",
            )
        
        # Detect changes
        detector = ChangeDetector(token)
        
        try:
            detection_result = await detector.detect_changes(
                db=db,
                config_id=config_id,
            )
            
            # Count editable vs readonly changes
            editable_changes = 0
            readonly_changes = 0
            
            for row_change in detection_result.row_changes:
                for cell_change in row_change.cell_changes:
                    if cell_change.is_editable:
                        editable_changes += 1
                    else:
                        readonly_changes += 1
            
            return {
                "config_id": config_id,
                "has_changes": detection_result.has_changes,
                "total_changed_rows": detection_result.total_changed_rows,
                "total_changed_cells": detection_result.total_changed_cells,
                "editable_changes": editable_changes,
                "readonly_changes": readonly_changes,
                "last_check_at": detection_result.detected_at.isoformat(),
                "error": detection_result.error,
            }
            
        finally:
            await detector.close()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_changes_summary_failed", config_id=config_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# REVERSE SYNC ENDPOINTS (SHEET → BITRIX24)
# ============================================================================


@router.post("/reverse-sync/sync-all/{config_id}")
async def sync_all_changes_to_bitrix(
    config_id: int,
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Sync all detected changes from Google Sheets to Bitrix24
    
    Path params:
    - config_id: Sync configuration ID
    
    Query params:
    - user_id: User ID
    
    Response:
    {
        "started_at": "2025-11-29T10:00:00",
        "completed_at": "2025-11-29T10:00:05",
        "total_rows": 5,
        "successful": 4,
        "failed": 1,
        "skipped": 0,
        "results": [...]
    }
    """
    from app.services.change_detector import ChangeDetector
    from app.services.reverse_sync import ReverseSyncService
    
    try:
        # Get user token for Google Sheets
        stmt = select(UserSheetsToken).where(UserSheetsToken.user_id == user_id)
        result = await db.execute(stmt)
        token_record = result.scalar_one_or_none()
        
        if not token_record or not token_record.access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google Sheets bağlantısı bulunamadı",
            )
        
        # Get config for Bitrix webhook URL
        stmt_config = select(SheetSyncConfig).where(SheetSyncConfig.id == config_id)
        result_config = await db.execute(stmt_config)
        config = result_config.scalars().first()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Yapılandırma bulunamadı",
            )
        
        if not config.webhook_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bitrix24 webhook URL tanımlı değil",
            )
        
        # Get valid access token
        oauth_auth = GoogleSheetsAuth()
        token = await oauth_auth.get_valid_access_token(db, user_id)
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token yenileme başarısız",
            )
        
        # Detect changes first
        detector = ChangeDetector(token)
        
        try:
            detection_result = await detector.detect_changes(db, config_id)
            
            if not detection_result.has_changes:
                return {
                    "started_at": datetime.utcnow().isoformat(),
                    "completed_at": datetime.utcnow().isoformat(),
                    "total_rows": 0,
                    "successful": 0,
                    "failed": 0,
                    "skipped": 0,
                    "message": "Değişiklik bulunamadı",
                    "results": [],
                }
            
            # Sync changes to Bitrix24
            reverse_sync = ReverseSyncService(
                bitrix_webhook_url=config.webhook_url,
                access_token=token,
            )
            
            batch_result = await reverse_sync.sync_all_changes(
                db=db,
                config_id=config_id,
                detection_result=detection_result,
            )
            
            return batch_result.to_dict()
            
        finally:
            await detector.close()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("sync_all_changes_failed", config_id=config_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/reverse-sync/sync-rows/{config_id}")
async def sync_selected_rows_to_bitrix(
    config_id: int,
    user_id: str = Query(...),
    row_numbers: List[int] = Query(..., description="Row numbers to sync"),
    db: AsyncSession = Depends(get_db),
):
    """
    Sync selected rows from Google Sheets to Bitrix24
    
    Path params:
    - config_id: Sync configuration ID
    
    Query params:
    - user_id: User ID
    - row_numbers: List of row numbers to sync
    
    Response:
    {
        "started_at": "2025-11-29T10:00:00",
        "completed_at": "2025-11-29T10:00:05",
        "total_rows": 3,
        "successful": 2,
        "failed": 1,
        "results": [...]
    }
    """
    from app.services.change_detector import ChangeDetector
    from app.services.reverse_sync import ReverseSyncService
    
    try:
        # Get user token
        stmt = select(UserSheetsToken).where(UserSheetsToken.user_id == user_id)
        result = await db.execute(stmt)
        token_record = result.scalar_one_or_none()
        
        if not token_record or not token_record.access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google Sheets bağlantısı bulunamadı",
            )
        
        # Get config
        stmt_config = select(SheetSyncConfig).where(SheetSyncConfig.id == config_id)
        result_config = await db.execute(stmt_config)
        config = result_config.scalars().first()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Yapılandırma bulunamadı",
            )
        
        if not config.webhook_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bitrix24 webhook URL tanımlı değil",
            )
        
        # Get valid access token
        oauth_auth = GoogleSheetsAuth()
        token = await oauth_auth.get_valid_access_token(db, user_id)
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token yenileme başarısız",
            )
        
        # Detect changes
        detector = ChangeDetector(token)
        
        try:
            detection_result = await detector.detect_changes(db, config_id)
            
            # Filter to only selected rows
            selected_changes = [
                row for row in detection_result.row_changes
                if row.row_number in row_numbers
            ]
            
            if not selected_changes:
                return {
                    "started_at": datetime.utcnow().isoformat(),
                    "completed_at": datetime.utcnow().isoformat(),
                    "total_rows": 0,
                    "successful": 0,
                    "failed": 0,
                    "skipped": 0,
                    "message": "Seçilen satırlarda değişiklik bulunamadı",
                    "results": [],
                }
            
            # Sync selected rows
            reverse_sync = ReverseSyncService(
                bitrix_webhook_url=config.webhook_url,
                access_token=token,
            )
            
            batch_result = await reverse_sync.sync_selected_rows(
                db=db,
                config_id=config_id,
                row_changes=selected_changes,
            )
            
            return batch_result.to_dict()
            
        finally:
            await detector.close()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("sync_selected_rows_failed", config_id=config_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/reverse-sync/sync-row/{config_id}/{row_number}")
async def sync_single_row_to_bitrix(
    config_id: int,
    row_number: int,
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Sync a single row from Google Sheets to Bitrix24
    
    Path params:
    - config_id: Sync configuration ID
    - row_number: Row number to sync
    
    Query params:
    - user_id: User ID
    
    Response:
    {
        "row_number": 2,
        "entity_id": "123",
        "success": true,
        "fields_synced": ["Name", "Email"],
        "synced_at": "2025-11-29T10:00:00"
    }
    """
    from app.services.change_detector import ChangeDetector
    from app.services.reverse_sync import ReverseSyncService
    
    try:
        # Get user token
        stmt = select(UserSheetsToken).where(UserSheetsToken.user_id == user_id)
        result = await db.execute(stmt)
        token_record = result.scalar_one_or_none()
        
        if not token_record or not token_record.access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google Sheets bağlantısı bulunamadı",
            )
        
        # Get config
        stmt_config = select(SheetSyncConfig).where(SheetSyncConfig.id == config_id)
        result_config = await db.execute(stmt_config)
        config = result_config.scalars().first()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Yapılandırma bulunamadı",
            )
        
        if not config.webhook_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bitrix24 webhook URL tanımlı değil",
            )
        
        # Get valid access token
        oauth_auth = GoogleSheetsAuth()
        token = await oauth_auth.get_valid_access_token(db, user_id)
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token yenileme başarısız",
            )
        
        # Get row details
        detector = ChangeDetector(token)
        
        try:
            detection_result = await detector.detect_changes(db, config_id)
            
            # Find the specific row
            row_change = next(
                (r for r in detection_result.row_changes if r.row_number == row_number),
                None
            )
            
            if not row_change:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Bu satırda değişiklik bulunamadı",
                )
            
            if not row_change.entity_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Entity ID bulunamadı",
                )
            
            # Prepare changes
            changes = {
                cell.column_name: cell.new_value
                for cell in row_change.cell_changes
                if cell.is_editable
            }
            
            if not changes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Güncellenebilir değişiklik bulunamadı",
                )
            
            # Sync row
            reverse_sync = ReverseSyncService(
                bitrix_webhook_url=config.webhook_url,
                access_token=token,
            )
            
            sync_result = await reverse_sync.sync_single_row(
                db=db,
                config_id=config_id,
                row_number=row_number,
                changes=changes,
                entity_id=row_change.entity_id,
            )
            
            return sync_result.to_dict()
            
        finally:
            await detector.close()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("sync_single_row_failed", config_id=config_id, row=row_number, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/reverse-sync/history/{config_id}")
async def get_reverse_sync_history(
    config_id: int,
    user_id: str = Query(...),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Max results"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get reverse sync history for a configuration
    
    Path params:
    - config_id: Sync configuration ID
    
    Query params:
    - user_id: User ID
    - status_filter: Optional status filter (pending, syncing, completed, failed)
    - limit: Max results (default 50)
    
    Response:
    [
        {
            "id": 1,
            "entity_id": 123,
            "row_number": 2,
            "status": "completed",
            "changed_fields": {"Name": "John"},
            "error": null,
            "created_at": "2025-11-29T10:00:00",
            "synced_at": "2025-11-29T10:00:01"
        }
    ]
    """
    from app.services.reverse_sync import ReverseSyncService
    
    try:
        # Verify user owns this config
        stmt = select(SheetSyncConfig).where(
            SheetSyncConfig.id == config_id,
            SheetSyncConfig.user_id == user_id,
        )
        result = await db.execute(stmt)
        config = result.scalars().first()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Yapılandırma bulunamadı",
            )
        
        reverse_sync = ReverseSyncService(
            bitrix_webhook_url=config.webhook_url or "",
        )
        
        history = await reverse_sync.get_sync_history(
            db=db,
            config_id=config_id,
            status_filter=status_filter,
            limit=limit,
        )
        
        return history
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_reverse_sync_history_failed", config_id=config_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/reverse-sync/retry/{config_id}")
async def retry_failed_syncs(
    config_id: int,
    user_id: str = Query(...),
    log_ids: Optional[List[int]] = Query(None, description="Specific log IDs to retry"),
    db: AsyncSession = Depends(get_db),
):
    """
    Retry failed sync operations
    
    Path params:
    - config_id: Sync configuration ID
    
    Query params:
    - user_id: User ID
    - log_ids: Optional specific log IDs to retry
    
    Response:
    {
        "started_at": "2025-11-29T10:00:00",
        "completed_at": "2025-11-29T10:00:05",
        "total_rows": 3,
        "successful": 2,
        "failed": 1,
        "results": [...]
    }
    """
    from app.services.reverse_sync import ReverseSyncService
    
    try:
        # Verify user owns this config
        stmt = select(SheetSyncConfig).where(
            SheetSyncConfig.id == config_id,
            SheetSyncConfig.user_id == user_id,
        )
        result = await db.execute(stmt)
        config = result.scalars().first()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Yapılandırma bulunamadı",
            )
        
        if not config.webhook_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bitrix24 webhook URL tanımlı değil",
            )
        
        reverse_sync = ReverseSyncService(
            bitrix_webhook_url=config.webhook_url,
        )
        
        batch_result = await reverse_sync.retry_failed_rows(
            db=db,
            config_id=config_id,
            log_ids=log_ids,
        )
        
        return batch_result.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("retry_failed_syncs_failed", config_id=config_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# CONFLICT MANAGEMENT ENDPOINTS
# ============================================================================


@router.get("/conflicts/detect/{config_id}")
async def detect_conflicts(
    config_id: int,
    user_id: str = Query(..., description="Kullanıcı ID"),
    row_numbers: Optional[str] = Query(None, description="Virgülle ayrılmış satır numaraları"),
    check_all: bool = Query(False, description="Tüm satırları kontrol et"),
    db: AsyncSession = Depends(get_db),
):
    """
    Çakışmaları algıla
    
    Bitrix24 ve Google Sheets arasındaki çakışmaları tespit eder.
    Aynı anda iki yerde değişen alanları bulur.
    """
    from app.services.conflict_manager import ConflictManager
    
    try:
        # Verify user owns this config
        stmt = select(SheetSyncConfig).where(
            SheetSyncConfig.id == config_id,
            SheetSyncConfig.user_id == user_id,
        )
        result = await db.execute(stmt)
        config = result.scalars().first()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Yapılandırma bulunamadı",
            )
        
        # Parse row numbers if provided
        rows = None
        if row_numbers:
            rows = [int(r.strip()) for r in row_numbers.split(",")]
        
        # Detect conflicts
        manager = ConflictManager(db, config)
        detection_result = await manager.detect_conflicts(
            row_numbers=rows,
            check_all=check_all
        )
        
        # Convert to dict
        return {
            "config_id": detection_result.config_id,
            "detected_at": detection_result.detected_at.isoformat(),
            "total_rows_checked": detection_result.total_rows_checked,
            "conflicts_found": detection_result.conflicts_found,
            "has_conflicts": detection_result.has_conflicts,
            "row_conflicts": [
                {
                    "row_number": rc.row_number,
                    "entity_id": rc.entity_id,
                    "entity_type": rc.entity_type,
                    "conflict_count": rc.conflict_count,
                    "unresolved_count": rc.unresolved_count,
                    "field_conflicts": [
                        {
                            "field_name": fc.field_name,
                            "column_name": fc.column_name,
                            "column_index": fc.column_index,
                            "bitrix_field": fc.bitrix_field,
                            "bitrix_value": fc.bitrix_value,
                            "sheet_value": fc.sheet_value,
                            "conflict_type": fc.conflict_type.value,
                            "suggested_resolution": fc.suggested_resolution.value,
                            "resolved": fc.resolved,
                        }
                        for fc in rc.field_conflicts
                    ]
                }
                for rc in detection_result.row_conflicts
            ],
            "error": detection_result.error
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("detect_conflicts_failed", config_id=config_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/conflicts/resolve/{config_id}")
async def resolve_conflict(
    config_id: int,
    user_id: str = Query(..., description="Kullanıcı ID"),
    row_number: int = Query(..., description="Satır numarası"),
    field_name: str = Query(..., description="Alan adı"),
    resolution: str = Query(..., description="Çözüm stratejisi: use_bitrix, use_sheet, skip"),
    custom_value: Optional[str] = Query(None, description="Özel değer (merge için)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Tek bir çakışmayı çöz
    
    Args:
        resolution: use_bitrix, use_sheet, merge, skip
    """
    from app.services.conflict_manager import ConflictManager, ResolutionStrategy
    
    try:
        # Verify user owns this config
        stmt = select(SheetSyncConfig).where(
            SheetSyncConfig.id == config_id,
            SheetSyncConfig.user_id == user_id,
        )
        result = await db.execute(stmt)
        config = result.scalars().first()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Yapılandırma bulunamadı",
            )
        
        # Parse resolution strategy
        try:
            strategy = ResolutionStrategy(resolution)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Geçersiz çözüm stratejisi: {resolution}. Geçerli değerler: use_bitrix, use_sheet, merge, skip"
            )
        
        # Resolve conflict
        manager = ConflictManager(db, config)
        result = await manager.resolve_conflict(
            row_number=row_number,
            field_name=field_name,
            resolution=strategy,
            custom_value=custom_value
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("resolve_conflict_failed", config_id=config_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/conflicts/resolve-row/{config_id}")
async def resolve_row_conflicts(
    config_id: int,
    user_id: str = Query(..., description="Kullanıcı ID"),
    row_number: int = Query(..., description="Satır numarası"),
    resolution: str = Query(..., description="Çözüm stratejisi: use_bitrix, use_sheet"),
    db: AsyncSession = Depends(get_db),
):
    """
    Bir satırdaki tüm çakışmaları aynı strateji ile çöz
    """
    from app.services.conflict_manager import ConflictManager, ResolutionStrategy
    
    try:
        # Verify user owns this config
        stmt = select(SheetSyncConfig).where(
            SheetSyncConfig.id == config_id,
            SheetSyncConfig.user_id == user_id,
        )
        result = await db.execute(stmt)
        config = result.scalars().first()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Yapılandırma bulunamadı",
            )
        
        # Parse resolution strategy
        try:
            strategy = ResolutionStrategy(resolution)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Geçersiz çözüm stratejisi: {resolution}"
            )
        
        # Resolve all conflicts in row
        manager = ConflictManager(db, config)
        result = await manager.resolve_row_conflicts(
            row_number=row_number,
            resolution=strategy
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("resolve_row_conflicts_failed", config_id=config_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/conflicts/history/{config_id}")
async def get_conflict_history(
    config_id: int,
    user_id: str = Query(..., description="Kullanıcı ID"),
    limit: int = Query(50, ge=1, le=200, description="Kayıt limiti"),
    db: AsyncSession = Depends(get_db),
):
    """
    Çakışma geçmişini getir
    
    Geçmiş senkronizasyon loglarından çakışma geçmişini döner.
    """
    from app.services.conflict_manager import ConflictManager
    
    try:
        # Verify user owns this config
        stmt = select(SheetSyncConfig).where(
            SheetSyncConfig.id == config_id,
            SheetSyncConfig.user_id == user_id,
        )
        result = await db.execute(stmt)
        config = result.scalars().first()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Yapılandırma bulunamadı",
            )
        
        manager = ConflictManager(db, config)
        history = await manager.get_conflict_history(limit=limit)
        
        return {
            "config_id": config_id,
            "history": history,
            "count": len(history)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_conflict_history_failed", config_id=config_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
