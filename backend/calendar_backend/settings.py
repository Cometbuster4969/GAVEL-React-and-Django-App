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
_use_mock = os.getenv("USE_MONGOMOCK", "false").lower() == "true"
try:
    mongoengine.connect(host=MONGODB_URI, uuidRepresentation="standard", connectTimeoutMS=3000, serverSelectionTimeoutMS=3000)
    # Verify connectivity; fall back to mongomock if unavailable (e.g., CI without mongod)
    if _use_mock:
        raise Exception("Forced mongomock via USE_MONGOMOCK")
    from mongoengine.connection import get_db

    get_db().command("ping")
except Exception:
    try:
        import mongomock  # type: ignore

        mongoengine.disconnect_all()
        mongoengine.connect(
            host=MONGODB_URI,
            uuidRepresentation="standard",
            mongo_client_class=mongomock.MongoClient,
        )
    except Exception:
        # If mongomock also unavailable, re-raise original connection for health to report degraded
        pass

# Auto-seed in-memory mongomock when real Mongo not available (so setup.sh + server each have data in their own process)
try:
    from mongoengine.connection import get_db as _get_db

    _db = _get_db()
    # Only seed if we are using mongomock (in-memory) and collections are empty
    _is_mock = "mongomock" in str(type(_db.client)).lower() or "mongomock" in str(_db.client.__class__).lower()
    if _is_mock:
        from apps.gavel.models import GavelUser as _GU

        if _GU.objects.count() == 0:
            # Import and run seed in same process so data is visible to this server
            import pathlib as _pl
            import importlib.util as _ilu

            _seed_path = _pl.Path(__file__).resolve().parent.parent / "scripts" / "seed.py"
            if _seed_path.exists():
                _spec = _ilu.spec_from_file_location("gavel_seed", str(_seed_path))
                _mod = _ilu.module_from_spec(_spec)
                _spec.loader.exec_module(_mod)
                try:
                    _mod.seed()
                except Exception:
                    pass
except Exception:
    pass

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
    "URL_FORMAT_OVERRIDE": None,
}
USE_TZ = True
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
