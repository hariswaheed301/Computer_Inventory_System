# app/config.py
import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

class Config:
    # Environment
    APP_ENV = os.environ.get('APP_ENV', 'development').lower()
    HOST = os.environ.get('HOST', '127.0.0.1')
    PORT = int(os.environ.get('PORT', 5000))
    
     # Default account passwords (only used during first database seed)
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
    STORE_PASSWORD = os.environ.get('STORE_PASSWORD')
    
    # Secret Key (must be set in production)
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default-dev-key')
    
    # Database
    DATABASE_URL = os.environ.get('DATABASE_URL')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    DB_NAME = os.environ.get('DB_NAME', 'computer_inventory')
    DB_USER = os.environ.get('DB_USER', 'postgres')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    
    
    # Session Security
    SESSION_COOKIE_SECURE = APP_ENV == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'strict' if APP_ENV == 'production' else 'lax'

    # Flask login session cookie
    SESSION_COOKIE_NAME = 'inventory_session'

    # 15 minutes inactivity timeout
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=15)

    # Refresh expiry on every request
    SESSION_REFRESH_EACH_REQUEST = True

    
    
    # Scheme & Redirect
    PREFERRED_URL_SCHEME = 'https' if APP_ENV == 'production' else 'http'
    
    # Admin Recovery Code for Password Reset
    ADMIN_RECOVERY_CODE = os.environ.get('ADMIN_RECOVERY_CODE', '')

    # Rate Limiter Config
    RATELIMIT_STORAGE_URI = os.environ.get(
    "REDIS_URL",
    "memory://"
)

    RATELIMIT_DEFAULT = "200/day;50/hour" 
   
    ADMIN_CONTACT_EMAIL = os.environ.get(
    "ADMIN_CONTACT_EMAIL",
    "admin@techstore.com"
)

   