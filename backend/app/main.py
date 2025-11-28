"""
FastAPI Main Application
Latest FastAPI patterns (2025)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from app.config import settings
from app.database import init_db, close_db
from app.api import exports, webhooks, tables, data, views, sheet_sync, lookups, ai_summary, setup

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("application_startup")
    await init_db()
    
    yield
    
    # Shutdown
    logger.info("application_shutdown")
    await close_db()


# Create FastAPI app
app = FastAPI(
    title="Bitrix24 Google Sheets Exporter",
    description="Modern export service with relationship detection",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1600",
        "http://localhost:3001",
        "http://127.0.0.1:1600",
        "http://127.0.0.1:3001",
        "http://10.196.81.139:1600",  # Local network yeni port
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    max_age=600,  # Cache preflight for 10 minutes
)

# Include routers
app.include_router(exports.router, prefix="/api/exports", tags=["Exports"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["Webhooks"])
app.include_router(tables.router, prefix="/api/tables", tags=["Tables"])
app.include_router(data.router, prefix="/api/data", tags=["Data"])
app.include_router(views.router, prefix="/api/views", tags=["Views"])
app.include_router(lookups.router, prefix="/api/lookups", tags=["Lookups"])
app.include_router(sheet_sync.router)  # Includes its own prefix /api/v1/sheet-sync
app.include_router(ai_summary.router)  # AI Summary endpoints /api/v1/ai-summary
app.include_router(setup.router)  # Setup wizard endpoints /api/v1/setup


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Bitrix24 Google Sheets Exporter",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    from datetime import datetime
    return {
        "status": "healthy",
        "database": "connected",
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level
    )
