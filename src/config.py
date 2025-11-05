"""
Veritabanı Konfigürasyonu
"""
import os
from dotenv import load_dotenv

load_dotenv()

# PostgreSQL Bağlantı Ayarları
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'bitsheet_db')
DB_USER = os.getenv('DB_USER', 'bitsheet')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'bitsheet123')

# Veritabanı URL'si
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# SQLAlchemy Ayarları
SQLALCHEMY_DATABASE_URI = DATABASE_URL
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ECHO = os.getenv('SQLALCHEMY_ECHO', 'False') == 'True'

# Flask Ayarları
FLASK_ENV = os.getenv('FLASK_ENV', 'development')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

class Config:
    """Temel Konfigürasyon"""
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = SECRET_KEY

class DevelopmentConfig(Config):
    """Geliştirme Ortamı Konfigürasyonu"""
    DEBUG = True
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    """Üretim Ortamı Konfigürasyonu"""
    DEBUG = False
    SQLALCHEMY_ECHO = False

class TestingConfig(Config):
    """Test Ortamı Konfigürasyonu"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

# Ortama göre doğru config'i seç
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(env=None):
    """Ortama göre uygun konfigürasyonu döndür"""
    if env is None:
        env = FLASK_ENV
    return config.get(env, config['default'])
