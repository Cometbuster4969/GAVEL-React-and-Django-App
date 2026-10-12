import os
from pathlib import Path

import mongoengine
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if os.getenv("NODE_ENV", "development") == "production":
        raise ValueError("DJANGO_SECRET_KEY must be set in production.")
    SECRET_KEY = "gavel-django-development-key"

DEBUG = os.getenv("NODE_ENV", "development") == "development"

# Restrict allowed hosts in production; allow all only in development
ALLOWED_HOSTS = ["*"] if DEBUG else ["localhost", "127.0.0.1", ".internal", ".e2b.app"]

# JWT: enforce production secret; shorter expiry in production (2h default)
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    if not DEBUG:
        raise ValueError("JWT_SECRET must be set and must not be the default demo value in production.")
    JWT_SECRET = "gavel-local-demo-secret-change-before-deployment"
JWT_ISSUER = os.getenv("JWT_ISSUER", "gavel-api")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "gavel-app")
JWT_LIFETIME = int(os.getenv("JWT_LIFETIME_SECONDS", "7200"))  # 2h production default; 24h (86400) only for dev

def _mongo_location(uri):
    from urllib.parse import urlsplit

    parts = urlsplit(uri)
    host = parts.hostname or "127.0.0.1"
    port = parts.port or 27017
    name = (parts.path or "/").strip("/") or "gavel_db"
    return f"{host}:{port}/{name}"


# MongoDB URI: never expose credentials in URI without TLS in production
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017/gavel_db")
try:
    mongoengine.connect(
        host=MONGODB_URI,
        uuidRepresentation="standard",
        connectTimeoutMS=3000,
        serverSelectionTimeoutMS=3000,
    )
    from mongoengine.connection import get_db

    get_db().command("ping")
except Exception as exc:
    mongoengine.disconnect_all()
    location = _mongo_location(MONGODB_URI)
    raise RuntimeError(
        f"Gavel could not reach MongoDB at {location} within 3 seconds. "
        "Start mongod (default 127.0.0.1:27017) or set MONGODB_URI, then retry. "
        "The API will not start with an in-memory database."
    ) from exc

INSTALLED_APPS = ["corsheaders", "rest_framework", "apps.gavel.apps.GavelConfig"]
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "calendar_backend.security_middleware.HTTPSRedirectMiddleware",
    "calendar_backend.security_middleware.RateLimitMiddleware",
    "calendar_backend.security_middleware.SecretValidationMiddleware",
]
# CORS: allow all only in development; restrict to known origins in production
CORS_ALLOW_ALL_ORIGINS = DEBUG
_cors_env = os.getenv("CORS_ALLOWED_ORIGINS", "").strip()
CORS_ALLOWED_ORIGINS = [] if DEBUG else [
    origin.strip()
    for origin in (_cors_env or "http://localhost:3000,http://127.0.0.1:3000").split(",")
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = not DEBUG  # Only send credentials over HTTPS/restricted origins
ROOT_URLCONF = "calendar_backend.urls"
DATABASES = {}
TEMPLATES = []
REST_FRAMEWORK = {
    "UNAUTHENTICATED_USER": None,
    "EXCEPTION_HANDLER": "apps.shared.errors.api_exception_handler",
    "DEFAULT_RENDERER_CLASSES": ["apps.shared.rendering.ApiRenderer"],
    "URL_FORMAT_OVERRIDE": None,
}
USE_TZ = True
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Shared MongoDB rate limiter. Trust only proxy networks controlled by the operator.
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
TRUSTED_PROXY_CIDRS = [value.strip() for value in os.getenv("TRUSTED_PROXY_CIDRS", "").split(",") if value.strip()]
if RATE_LIMIT_MAX < 1 or RATE_LIMIT_WINDOW < 1:
    raise ValueError("Rate-limit maximum and window must be positive.")
