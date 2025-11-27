"""
Application Configuration
Uses Pydantic v2 Settings Management
"""
from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )
    
    # Database - individual components
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_name: str = Field(default="bitsheet_db", alias="DB_NAME")
    db_user: str = Field(default="bitsheet", alias="DB_USER")
    db_password: str = Field(default="bitsheet123", alias="DB_PASSWORD")
    
    # Database URL (computed from components if not provided)
    database_url: Optional[str] = Field(default=None)
    
    @property
    def get_database_url(self) -> str:
        """Get database URL, either from DATABASE_URL env or constructed from components"""
        if self.database_url:
            return str(self.database_url)
        # Construct from individual components
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    # Bitrix24
    bitrix24_webhook_url: str = Field(
        default="https://sistem.japonkonutlari.com/rest/1/g2gj8wxjs6izkzhy/"
    )
    
    # Google Sheets
    google_sheets_webhook_url: str = Field(
        default="https://script.google.com/macros/s/AKfycbzEjDSmOmQDQVx_q_vhfHtd55HXe-puCqU9Q0XYmgL-Iv7zPzdWynDDBW_1QkPZlWcWGw/exec"
    )
    google_service_account_json: Optional[str] = Field(default=None)
    
    # Google OAuth (User Authentication for Sheets)
    google_client_id: str = Field(default="")
    google_client_secret: str = Field(default="")
    google_redirect_uri: str = Field(default="http://localhost:1600/sheet-sync/oauth/callback")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")
    
    # API Server
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_reload: bool = Field(default=True)
    log_level: str = Field(default="info")
    frontend_url: str = Field(default="http://localhost:1600")
    
    # Security
    secret_key: str = Field(default="dev-secret-key-change-in-production")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    
    # Export Settings
    default_batch_size: int = Field(default=500)
    max_batch_size: int = Field(default=1000)
    export_timeout_seconds: int = Field(default=300)
    
    # Turkish Date Format
    turkish_date_format: str = Field(default="DD/MM/YYYY")
    turkish_time_format: str = Field(default="HH:mm:ss")
    
    # Reverse Sync Settings
    reverse_sync_webhook_url: str = Field(
        default="https://etablo.japonkonutlari.com/api/v1/sheet-sync/webhook"
    )
    reverse_sync_enabled: bool = Field(default=True)


# Global settings instance
settings = Settings()
