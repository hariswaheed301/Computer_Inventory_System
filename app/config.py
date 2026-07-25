# app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    APP_ENV = os.environ.get('APP_ENV', 'development').lower()
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default-dev-key')
    DATABASE_URL = os.environ.get('DATABASE_URL')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    DB_NAME = os.environ.get('DB_NAME', 'computer_inventory')
    DB_USER = os.environ.get('DB_USER', 'postgres')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    
    # Session Security
    SESSION_COOKIE_SECURE = APP_ENV == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_NAME = '__Secure-session' if APP_ENV == 'production' else 'session'
    PERMANENT_SESSION_LIFETIME = 900  # 15 minutes
    
    # Scheme & Redirect
    PREFERRED_URL_SCHEME = 'https' if APP_ENV == 'production' else 'http'
    
    # Rate Limiter Config
    RATELIMIT_STORAGE_URL = "memory://"
    RATELIMIT_DEFAULT = "200/day;50/hour"
