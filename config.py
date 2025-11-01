"""
PiCMS Configuration Module
Handles environment variables and application settings
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class"""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///database.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.getenv('SQLALCHEMY_ECHO', 'False').lower() == 'true'
    
    # File Upload
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'videos')
    THUMBNAIL_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'thumbnails')
    MAX_CONTENT_MB = int(os.getenv('MAX_CONTENT_MB', '500'))
    MAX_CONTENT_LENGTH = MAX_CONTENT_MB * 1024 * 1024
    
    # Parse allowed extensions from env
    _extensions = os.getenv('ALLOWED_EXTENSIONS', 'mp4,avi,mkv,mov,wmv,flv,webm')
    ALLOWED_EXTENSIONS = set(_extensions.split(','))
    
    # Logging
    LOG_FOLDER = os.path.join(os.path.dirname(__file__), 'logs')
    API_LOG_FILE = os.path.join(LOG_FOLDER, 'api.log')
    APP_LOG_FILE = os.path.join(LOG_FOLDER, 'app.log')
    
    # Security
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    BCRYPT_LOG_ROUNDS = 12
    
    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
    
    # Rate Limiting
    RATELIMIT_ENABLED = os.getenv('RATELIMIT_ENABLED', 'True').lower() == 'true'
    RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL', 'memory://')
    API_RATE_LIMIT = int(os.getenv('API_RATE_LIMIT', '60'))
    
    # Device Status
    DEVICE_TIMEOUT_MINUTES = int(os.getenv('DEVICE_TIMEOUT_MINUTES', '5'))
    DEVICE_CLEANUP_DAYS = int(os.getenv('DEVICE_CLEANUP_DAYS', '90'))
    
    # Admin credentials (for initial setup)
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
    
    # Backup Settings
    BACKUP_FOLDER = os.path.join(os.path.dirname(__file__), 'backups')
    BACKUP_RETENTION_DAYS = int(os.getenv('BACKUP_RETENTION_DAYS', '30'))
    BACKUP_SCHEDULE_ENABLED = os.getenv('BACKUP_SCHEDULE_ENABLED', 'True').lower() == 'true'
    BACKUP_SCHEDULE_HOUR = int(os.getenv('BACKUP_SCHEDULE_HOUR', '2'))  # 2 AM default
    BACKUP_EMAIL_NOTIFICATIONS = os.getenv('BACKUP_EMAIL_NOTIFICATIONS', 'False').lower() == 'true'
    BACKUP_EMAIL = os.getenv('BACKUP_EMAIL', '')
    
    # Email Settings (Phase 6)
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', '587'))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@picms.local')
    MAIL_MAX_EMAILS = int(os.getenv('MAIL_MAX_EMAILS', '10'))
    MAIL_SUPPRESS_SEND = os.getenv('MAIL_SUPPRESS_SEND', 'True').lower() == 'true'  # Default suppress in dev
    
    # Server
    FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    FLASK_PORT = int(os.getenv('FLASK_PORT', '5000'))
    
    @staticmethod
    def init_app(app):
        """Initialize application with config-specific settings"""
        # Create necessary directories
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.THUMBNAIL_FOLDER, exist_ok=True)
        os.makedirs(Config.LOG_FOLDER, exist_ok=True)
        os.makedirs(Config.BACKUP_FOLDER, exist_ok=True)


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv('DEV_DATABASE_URI', 'sqlite:///database.db')


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI', 'postgresql://user:pass@localhost/picms')
    
    @classmethod
    def init_app(cls, app):  # type: ignore
        Config.init_app(app)
        
        # Production-specific initialization
        import logging
        from logging.handlers import RotatingFileHandler
        
        # Setup file handler for production
        file_handler = RotatingFileHandler(
            cls.APP_LOG_FILE,
            maxBytes=10240000,
            backupCount=10
        )
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    WTF_CSRF_CHECK_DEFAULT = False


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
