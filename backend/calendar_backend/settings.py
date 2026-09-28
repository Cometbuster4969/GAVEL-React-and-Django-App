import os
from pathlib import Path

import mongoengine
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "gavel-django-development-key")
DEBUG = os.getenv("NODE_ENV", "development") == "development"
ALLOWED_HOSTS = ["*"]

JWT_SECRET = os.getenv("JWT_SECRET", "gavel-local-demo-secret-change-before-deployment")
JWT_ISSUER = "gavel-api"
JWT_AUDIENCE = "gavel-app"
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017/gavel_db")
mongoengine.connect(host=MONGODB_URI, uuidRepresentation="standard", connectTimeoutMS=3000, serverSelectionTimeoutMS=3000)

INSTALLED_APPS = ["corsheaders", "rest_framework", "apps.gavel"]
MIDDLEWARE = ["corsheaders.middleware.CorsMiddleware", "django.middleware.common.CommonMiddleware"]
CORS_ALLOW_ALL_ORIGINS = True
ROOT_URLCONF = "calendar_backend.urls"
DATABASES = {}
TEMPLATES = []
REST_FRAMEWORK = {
    "UNAUTHENTICATED_USER": None,
    "EXCEPTION_HANDLER": "apps.shared.errors.api_exception_handler",
    "DEFAULT_RENDERER_CLASSES": ["apps.shared.rendering.ApiRenderer"],
}
USE_TZ = True
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
