import os

# Superset specific config
ROW_LIMIT = 5000

# Flask App Builder configuration
# Your App secret key will be used for securely signing the session cookie
# and encrypting sensitive information on the database
SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "your-secret-key-change-in-production")

# The SQLAlchemy connection string to your database backend
# Using SQLite for simplicity - change to PostgreSQL if needed
SQLALCHEMY_DATABASE_URI = "sqlite:////app/superset_home/superset.db"

# Flask-WTF flag for CSRF
WTF_CSRF_ENABLED = True
WTF_CSRF_EXEMPT_LIST = []
WTF_CSRF_TIME_LIMIT = 60 * 60 * 24 * 365

# Set this API key to enable Mapbox visualizations
MAPBOX_API_KEY = os.environ.get("MAPBOX_API_KEY", "")

# Cache configuration for Redis
CACHE_CONFIG = {
    "CACHE_TYPE": "redis",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "superset_",
    "CACHE_REDIS_HOST": os.environ.get("REDIS_HOST", "redis"),
    "CACHE_REDIS_PORT": os.environ.get("REDIS_PORT", 6379),
    "CACHE_REDIS_DB": 1,
}

DATA_CACHE_CONFIG = {
    "CACHE_TYPE": "redis",
    "CACHE_DEFAULT_TIMEOUT": 86400,
    "CACHE_KEY_PREFIX": "superset_data_",
    "CACHE_REDIS_HOST": os.environ.get("REDIS_HOST", "redis"),
    "CACHE_REDIS_PORT": os.environ.get("REDIS_PORT", 6379),
    "CACHE_REDIS_DB": 2,
}

# Celery configuration for async queries
class CeleryConfig:
    BROKER_URL = f"redis://{os.environ.get('REDIS_HOST', 'redis')}:{os.environ.get('REDIS_PORT', 6379)}/0"
    CELERY_IMPORTS = ("superset.sql_lab", "superset.tasks")
    CELERY_RESULT_BACKEND = f"redis://{os.environ.get('REDIS_HOST', 'redis')}:{os.environ.get('REDIS_PORT', 6379)}/0"
    CELERY_ANNOTATIONS = {"tasks.add": {"rate_limit": "10/s"}}

CELERY_CONFIG = CeleryConfig

# Feature flags
FEATURE_FLAGS = {
    "ENABLE_TEMPLATE_PROCESSING": True,
    "ALERT_REPORTS": True,
    "DASHBOARD_NATIVE_FILTERS": True,
    "DASHBOARD_CROSS_FILTERS": True,
    "DASHBOARD_RBAC": True,
}

# Webdriver configuration for screenshots
WEBDRIVER_TYPE = "chrome"
WEBDRIVER_OPTION_ARGS = [
    "--headless",
    "--disable-gpu",
    "--no-sandbox",
    "--disable-dev-shm-usage",
]

# Enable or disable CORS
ENABLE_CORS = False

# Time grain configurations
TIME_GRAIN_ADDONS = {
    "PT5S": "5 seconds",
    "PT30S": "30 seconds",
    "PT1M": "1 minute",
    "PT5M": "5 minutes",
    "PT10M": "10 minutes",
    "PT15M": "15 minutes",
    "PT30M": "30 minutes",
    "PT1H": "1 hour",
}

# Additional database connections
PREVENT_UNSAFE_DB_CONNECTIONS = False

# SQL Lab settings
SQLLAB_ASYNC_TIME_LIMIT_SEC = 300
SQLLAB_TIMEOUT = 300
SUPERSET_WEBSERVER_TIMEOUT = 300
