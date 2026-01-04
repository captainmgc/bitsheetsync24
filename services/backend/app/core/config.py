"""
Application configuration

Port Configuration:
  - Frontend: 4000 (development) / 443 (production)
  - Backend:  4001 (development) / 443 (production via /api)
"""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    """Application settings"""
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Port Configuration
    FRONTEND_PORT: int = int(os.getenv("FRONTEND_PORT", "4000"))
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "4001"))
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "BitSheet24 Export API"
    VERSION: str = "1.0.0"
    
    # Database
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "bitsheet_db")
    DB_USER: str = os.getenv("DB_USER", "bitsheet")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "bitsheet123")
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # Google Sheets
    GOOGLE_CREDENTIALS_FILE: str = "google_credentials.json"
    GOOGLE_SHEETS_WEBHOOK_URL: str = "https://script.google.com/macros/s/AKfycbzEjDSmOmQDQVx_q_vhfHtd55HXe-puCqU9Q0XYmgL-Iv7zPzdWynDDBW_1QkPZlWcWGw/exec"
    
    # Bitrix24
    BITRIX_WEBHOOK_URL: str = os.getenv("BITRIX_WEBHOOK_URL", "https://sistem.japonkonutlari.com/rest/1/g2gj8wxjs6izkzhy/")
    
    # Export Settings
    BATCH_SIZE: int = 500
    MAX_BATCH_SIZE: int = 1000
    EXPORT_TIMEOUT: int = 300  # 5 minutes
    
    # Redis (for Celery)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Frontend URL (for CORS)
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", f"http://localhost:{os.getenv('FRONTEND_PORT', '4000')}")
    BACKEND_URL: str = os.getenv("BACKEND_URL", f"http://localhost:{os.getenv('BACKEND_PORT', '4001')}")
    
    # CORS - Dynamic based on environment
    @property
    def CORS_ORIGINS(self) -> List[str]:
        if self.ENVIRONMENT == "production":
            return [
                "https://etablo.japonkonutlari.com",
                self.FRONTEND_URL,
            ]
        # Development - allow all common ports
        return [
            f"http://localhost:{self.FRONTEND_PORT}",
            f"http://localhost:{self.BACKEND_PORT}",
            "http://localhost:3000",
            "http://localhost:4000",
            "http://localhost:4001",
            self.FRONTEND_URL,
        ]
    
    class Config:
        env_file = "../.env"  # Load from project root
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
