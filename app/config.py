"""
Configuration management for InfraZen
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from config.env
load_dotenv('config.env')

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'mysql+pymysql://infrazen_user:infrazen_password@localhost:3306/infrazen_dev?charset=utf8mb4'
    
    # MySQL-specific configuration
    # Connection pool settings for MySQL
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'connect_args': {
            'charset': 'utf8mb4'
        } if 'mysql' in os.environ.get('DATABASE_URL', '') else {}
    }
    
    # Google OAuth configuration
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', 'your-google-client-id')
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # Security
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

    # Recommendations feature flags
    RECOMMENDATIONS_ENABLED = os.environ.get('RECOMMENDATIONS_ENABLED', 'true').lower() == 'true'
    # Deprecated: debug cards removed; use logs instead
    RECOMMENDATIONS_DEBUG_MODE = False
    # Price check thresholds (defaults disabled)
    PRICE_CHECK_MIN_SAVINGS_RUB = float(os.environ.get('PRICE_CHECK_MIN_SAVINGS_RUB', '0'))
    PRICE_CHECK_MIN_SAVINGS_PERCENT = float(os.environ.get('PRICE_CHECK_MIN_SAVINGS_PERCENT', '0'))

    # Recommendation rules feature flags (disable by rule id, comma-separated)
    # Example: RECOMMENDATION_RULES_DISABLED="cost.price_check.cross_provider,cost.rightsize.cpu_underuse"
    _DISABLED_RAW = os.environ.get('RECOMMENDATION_RULES_DISABLED', '')
    RECOMMENDATION_RULES_DISABLED = set([s.strip() for s in _DISABLED_RAW.split(',') if s.strip()])

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    # Default to local MySQL for development
    # Example MySQL URL: mysql+pymysql://infrazen_user:password@localhost:3306/infrazen_dev?charset=utf8mb4
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'mysql+pymysql://infrazen_user:infrazen_password@localhost:3306/infrazen_dev?charset=utf8mb4'
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    # Production requires DATABASE_URL to be set
    # Example Beget MySQL: mysql+pymysql://user:pass@mysql.beget.com:3306/infrazen_prod?charset=utf8mb4
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_ECHO = False
    
    # Security settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://infrazen_user:infrazen_password@localhost:3306/infrazen_test?charset=utf8mb4'
    WTF_CSRF_ENABLED = False
