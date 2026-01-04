"""
Setup Wizard API Endpoints
Handles initial configuration and connection testing
"""

import os
import httpx
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
import structlog

from app.config import settings

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/setup", tags=["setup"])


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class BitrixWebhookRequest(BaseModel):
    """Request to save Bitrix24 webhook URL"""
    webhook_url: str = Field(..., description="Bitrix24 webhook URL")


class ConnectionStatusResponse(BaseModel):
    """Connection status response"""
    bitrix24: bool = False
    google: bool = False
    database: bool = True  # Always true if API is running


class BitrixTestResponse(BaseModel):
    """Bitrix24 test response"""
    success: bool
    message: str
    data: Optional[dict] = None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_env_file_path() -> str:
    """Get the path to the .env file"""
    # Check multiple locations
    possible_paths = [
        "/opt/bitsheet24/.env",
        "/opt/bitsheet24/backend/.env",
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        ".env"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # Default to root project .env
    return "/opt/bitsheet24/.env"


def update_env_file(key: str, value: str) -> bool:
    """Update or add a key-value pair in .env file"""
    env_path = get_env_file_path()
    
    try:
        # Read existing content
        lines = []
        key_found = False
        
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                lines = f.readlines()
            
            # Update existing key or keep other lines
            new_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith(f"{key}="):
                    new_lines.append(f"{key}={value}\n")
                    key_found = True
                else:
                    new_lines.append(line)
            lines = new_lines
        
        # Add key if not found
        if not key_found:
            lines.append(f"{key}={value}\n")
        
        # Write back
        with open(env_path, 'w') as f:
            f.writelines(lines)
        
        # Also update environment variable for current session
        os.environ[key] = value
        
        logger.info("env_file_updated", key=key, path=env_path)
        return True
        
    except Exception as e:
        logger.error("env_file_update_failed", key=key, error=str(e))
        return False


def get_env_value(key: str) -> Optional[str]:
    """Get value from .env file"""
    env_path = get_env_file_path()
    
    try:
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    stripped = line.strip()
                    if stripped.startswith(f"{key}="):
                        return stripped.split("=", 1)[1].strip('"').strip("'")
    except Exception as e:
        logger.error("env_file_read_failed", key=key, error=str(e))
    
    return os.getenv(key)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.get("/status")
async def get_connection_status() -> ConnectionStatusResponse:
    """
    Get current connection status for all services
    """
    # Check Bitrix24
    bitrix_url = get_env_value("BITRIX24_WEBHOOK_URL") or settings.bitrix24_webhook_url
    bitrix_configured = bool(bitrix_url and len(bitrix_url) > 20 and "/rest/" in bitrix_url)
    
    # Check Google (OAuth tokens)
    google_configured = bool(
        get_env_value("GOOGLE_CLIENT_ID") or 
        settings.google_client_id
    )
    
    return ConnectionStatusResponse(
        bitrix24=bitrix_configured,
        google=google_configured,
        database=True
    )


@router.post("/bitrix24")
async def save_bitrix24_webhook(request: BitrixWebhookRequest):
    """
    Save Bitrix24 webhook URL to .env file
    """
    webhook_url = request.webhook_url.strip()
    
    # Validate URL format
    if not webhook_url.startswith("https://"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook URL 'https://' ile başlamalıdır"
        )
    
    if "/rest/" not in webhook_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Geçersiz Bitrix24 webhook URL formatı"
        )
    
    # Ensure URL ends with /
    if not webhook_url.endswith("/"):
        webhook_url += "/"
    
    # Save to .env file
    success = update_env_file("BITRIX24_WEBHOOK_URL", webhook_url)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook URL kaydedilemedi"
        )
    
    logger.info("bitrix24_webhook_saved", url=webhook_url[:50] + "...")
    
    return {
        "success": True,
        "message": "Bitrix24 webhook URL başarıyla kaydedildi"
    }


@router.get("/test-bitrix24")
async def test_bitrix24_connection() -> BitrixTestResponse:
    """
    Test Bitrix24 connection using saved webhook URL
    """
    # Get webhook URL
    webhook_url = get_env_value("BITRIX24_WEBHOOK_URL") or settings.bitrix24_webhook_url
    
    if not webhook_url or len(webhook_url) < 20:
        return BitrixTestResponse(
            success=False,
            message="Bitrix24 webhook URL yapılandırılmamış"
        )
    
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # Test with profile.get to verify connection
            response = await client.get(f"{webhook_url}profile.json")
            
            if response.status_code != 200:
                return BitrixTestResponse(
                    success=False,
                    message=f"Bitrix24 API hatası: {response.status_code}"
                )
            
            profile_data = response.json()
            
            if "error" in profile_data:
                return BitrixTestResponse(
                    success=False,
                    message=f"Bitrix24 hatası: {profile_data.get('error_description', profile_data['error'])}"
                )
            
            # Get user info
            user_result = profile_data.get("result", {})
            user_name = f"{user_result.get('NAME', '')} {user_result.get('LAST_NAME', '')}".strip() or "Bilinmiyor"
            
            # Get deals count
            deals_response = await client.get(f"{webhook_url}crm.deal.list.json", params={"select[]": "ID"})
            deals_data = deals_response.json()
            deals_count = deals_data.get("total", 0)
            
            # Get contacts count
            contacts_response = await client.get(f"{webhook_url}crm.contact.list.json", params={"select[]": "ID"})
            contacts_data = contacts_response.json()
            contacts_count = contacts_data.get("total", 0)
            
            # Extract portal URL
            portal_url = webhook_url.split("/rest/")[0] if "/rest/" in webhook_url else "Bilinmiyor"
            
            return BitrixTestResponse(
                success=True,
                message="Bitrix24 bağlantısı başarılı!",
                data={
                    "portal_url": portal_url,
                    "user_name": user_name,
                    "deals_count": deals_count,
                    "contacts_count": contacts_count
                }
            )
            
    except httpx.TimeoutException:
        return BitrixTestResponse(
            success=False,
            message="Bitrix24 sunucusuna bağlanırken zaman aşımı oluştu"
        )
    except httpx.RequestError as e:
        return BitrixTestResponse(
            success=False,
            message=f"Bağlantı hatası: {str(e)}"
        )
    except Exception as e:
        logger.error("bitrix24_test_failed", error=str(e))
        return BitrixTestResponse(
            success=False,
            message=f"Beklenmeyen hata: {str(e)}"
        )


@router.get("/current-config")
async def get_current_config():
    """
    Get current configuration (masked for security)
    """
    webhook_url = get_env_value("BITRIX24_WEBHOOK_URL") or settings.bitrix24_webhook_url
    
    # Mask the webhook URL for display
    if webhook_url and len(webhook_url) > 30:
        masked_url = webhook_url[:30] + "..." + webhook_url[-10:]
    else:
        masked_url = "Yapılandırılmamış"
    
    return {
        "bitrix24_webhook_url": masked_url,
        "bitrix24_configured": bool(webhook_url and "/rest/" in webhook_url),
        "google_configured": bool(settings.google_client_id),
        "ai_providers": {
            "openai": bool(os.getenv("OPENAI_API_KEY")),
            "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
            "gemini": bool(os.getenv("GEMINI_API_KEY")),
            "openrouter": bool(os.getenv("OPENROUTER_API_KEY"))
        }
    }
