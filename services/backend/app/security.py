"""
Security Middleware for BitSheet24 API
Ensures API is only accessible from authenticated frontend sessions
"""
from fastapi import Request, HTTPException, Depends
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import structlog
import os

logger = structlog.get_logger()

# Internal API key that nginx will add to authenticated requests
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "bitsheet24-internal-secure-key-2026")

# Header name for internal authentication
INTERNAL_AUTH_HEADER = "X-Internal-Auth"

# Paths that don't require authentication (public endpoints)
PUBLIC_PATHS = [
    "/health",
    "/api/health",
    "/docs",
    "/openapi.json",
    "/redoc",
]

# Paths that require webhook authentication (different auth mechanism)
WEBHOOK_PATHS = [
    "/api/webhooks/",
    "/api/webhook/",
]


class InternalAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to ensure API requests come from authenticated sources.
    
    Authentication flow:
    1. User authenticates via NextAuth (Google OAuth)
    2. Frontend requests go through nginx
    3. Nginx adds X-Internal-Auth header for authenticated requests
    4. This middleware validates the header
    """
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Allow public paths
        if any(path.startswith(public_path) for public_path in PUBLIC_PATHS):
            return await call_next(request)
        
        # Webhook paths have their own authentication
        if any(path.startswith(webhook_path) for webhook_path in WEBHOOK_PATHS):
            return await call_next(request)
        
        # Check for internal auth header
        internal_auth = request.headers.get(INTERNAL_AUTH_HEADER)
        
        if not internal_auth:
            logger.warning(
                "unauthorized_api_access",
                path=path,
                client_ip=request.client.host if request.client else "unknown",
                headers=dict(request.headers)
            )
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Authentication required",
                    "error": "UNAUTHORIZED",
                    "message": "Bu API'ye erişmek için giriş yapmanız gerekmektedir."
                }
            )
        
        if internal_auth != INTERNAL_API_KEY:
            logger.warning(
                "invalid_api_key",
                path=path,
                client_ip=request.client.host if request.client else "unknown"
            )
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Invalid authentication",
                    "error": "FORBIDDEN",
                    "message": "Geçersiz kimlik doğrulama."
                }
            )
        
        # Valid authentication - proceed
        return await call_next(request)


def get_internal_auth_header():
    """Dependency for routes that need to verify internal auth"""
    api_key_header = APIKeyHeader(name=INTERNAL_AUTH_HEADER, auto_error=False)
    
    async def verify_internal_auth(api_key: str = Depends(api_key_header)):
        if not api_key or api_key != INTERNAL_API_KEY:
            raise HTTPException(
                status_code=401,
                detail="Authentication required"
            )
        return api_key
    
    return verify_internal_auth
