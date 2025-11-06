"""
Webhook Endpoints for Bitrix24 Events
"""
from fastapi import APIRouter, Request, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import structlog

from app.database import get_db
from app.schemas.export import ExportConfigCreate, ExportType
from app.services.export_manager import ExportManager

router = APIRouter()
logger = structlog.get_logger()


@router.post("/bitrix24")
async def bitrix24_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Receive Bitrix24 webhook events
    
    When data is updated in Bitrix24:
    1. Update local database (handled by sync daemon)
    2. Trigger Google Sheets export for changed entity
    """
    try:
        # Parse webhook payload
        payload = await request.json()
        
        event_type = payload.get("event")
        entity_type = payload.get("data", {}).get("FIELDS", {}).get("ENTITY_TYPE_ID")
        entity_id = payload.get("data", {}).get("FIELDS", {}).get("ID")
        
        logger.info("bitrix24_webhook_received",
                   event=event_type,
                   entity_type=entity_type,
                   entity_id=entity_id)
        
        # Map Bitrix24 event to our entity names
        entity_map = {
            "CRM_LEAD": "leads",
            "CRM_CONTACT": "contacts",
            "CRM_COMPANY": "companies",
            "CRM_DEAL": "deals",
            "CRM_ACTIVITY": "activities",
        }
        
        entity_name = entity_map.get(entity_type)
        
        if not entity_name:
            logger.warning("unknown_entity_type", entity_type=entity_type)
            return {"status": "ignored", "reason": "unknown_entity_type"}
        
        # Create auto-export configuration
        export_config = ExportConfigCreate(
            entity_name=entity_name,
            export_type=ExportType.INCREMENTAL,
            include_related=True,
            use_turkish_names=True,
            separate_date_time=True,
            batch_size=500,
            created_by="webhook"
        )
        
        # Create and run export in background
        manager = ExportManager(db)
        export_log = await manager.create_export(export_config)
        
        # Mark as webhook-triggered
        await db.execute(
            text("""
                UPDATE bitrix.export_logs 
                SET 
                    triggered_by_webhook = true,
                    webhook_event_type = :event_type,
                    webhook_entity_id = :entity_id
                WHERE id = :id
            """),
            {
                "id": export_log.id,
                "event_type": event_type,
                "entity_id": entity_id
            }
        )
        await db.commit()
        
        # Run export in background
        background_tasks.add_task(manager.run_export, export_log.id)
        
        logger.info("webhook_export_queued",
                   export_id=export_log.id,
                   entity=entity_name)
        
        return {
            "status": "queued",
            "export_id": export_log.id,
            "entity": entity_name
        }
        
    except Exception as e:
        logger.error("webhook_processing_error", error=str(e))
        return {"status": "error", "message": str(e)}


@router.get("/test")
async def test_webhook():
    """Test webhook endpoint"""
    return {
        "status": "ok",
        "message": "Webhook endpoint is working"
    }
