from datetime import timedelta

class Config:
    SECRET_KEY = 'dschool_secret_mihalych'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///users.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    WTF_CSRF_ENABLED = False
    WTF_CSRF_TIME_LIMIT = None
    
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False
    
    REMEMBER_COOKIE_NAME = 'remember_token'
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = False
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    
    TEMPLATES_AUTO_RELOAD = True
    SEND_FILE_MAX_AGE_DEFAULT = 0
    DEBUG = True
    ASSETS_DEBUG = True
    USE_OBFUSCATED = False
    MINIFY_HTML = False

class DevelopmentConfig(Config):
    DEBUG = True
    ASSETS_DEBUG = False
    USE_OBFUSCATED = False  
    MINIFY_HTML = False
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    
class ProductionConfig(Config):
    DEBUG = False
    ASSETS_DEBUG = False
    USE_OBFUSCATED = True
    MINIFY_HTML = True
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False