"""
Application configuration
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "BitSheet24 Export API"
    VERSION: str = "1.0.0"
    
    # Database
    DATABASE_URL: str = "postgresql://bitsheet:bitsheet123@localhost:5432/bitsheet_db"
    ASYNC_DATABASE_URL: str = "postgresql+asyncpg://bitsheet:bitsheet123@localhost:5432/bitsheet_db"
    
    # Google Sheets
    GOOGLE_CREDENTIALS_FILE: str = "google_credentials.json"
    GOOGLE_SHEETS_WEBHOOK_URL: str = "https://script.google.com/macros/s/AKfycbzEjDSmOmQDQVx_q_vhfHtd55HXe-puCqU9Q0XYmgL-Iv7zPzdWynDDBW_1QkPZlWcWGw/exec"
    
    # Bitrix24
    BITRIX_WEBHOOK_URL: str = "https://sistem.japonkonutlari.com/rest/1/g2gj8wxjs6izkzhy/"
    # Bu ayarlar env dosyasından da yüklenebilir bu şekilde daha güvenilirdir.
    
    # Export Settings
    BATCH_SIZE: int = 500
    MAX_BATCH_SIZE: int = 1000
    EXPORT_TIMEOUT: int = 300  # 5 minutes
    
    # Redis (for Celery)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
