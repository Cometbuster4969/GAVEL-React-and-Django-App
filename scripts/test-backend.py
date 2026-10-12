"""Run Gavel backend tests against a throwaway MongoDB database.

Creates a unique ``gavel_test_*`` database, runs the suite, and drops that
database even if tests fail. Never reads or writes the application database
(``gavel_db``) and never uses demo accounts.

Usage (from the repository root):

    bun test
"""
import os
import sys
import unittest
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

root = Path(__file__).resolve().parents[1]
backend = root / "backend"
sys.path.insert(0, str(backend))


def load_host_uri():
    for path in (backend / ".env", backend / ".env.example"):
        if path.exists():
            for line in path.read_text().splitlines():
                if line.startswith("MONGODB_URI="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017/gavel_db")


def fail(message):
    sys.stderr.write(message + "\n")
    sys.exit(1)


source = urlsplit(os.getenv("MONGODB_TEST_URI") or load_host_uri())
name = "gavel_test_" + uuid4().hex
uri = urlunsplit((source.scheme, source.netloc, "/" + name, source.query, ""))
os.environ["MONGODB_URI"] = uri
os.environ["DJANGO_SETTINGS_MODULE"] = "calendar_backend.settings"
os.environ["NODE_ENV"] = "development"
os.environ.pop("USE_MONGOMOCK", None)

try:
    import django

    django.setup()
except RuntimeError as exc:
    fail(str(exc))
except Exception as exc:
    fail(
        "Gavel tests could not reach MongoDB. Start mongod on 127.0.0.1:27017 "
        f"(or set MONGODB_URI) and retry with `bun test`.\n{exc}"
    )

from mongoengine.connection import get_db

db = get_db()
if not str(db.name).startswith("gavel_test_"):
    fail(f"Refusing to run tests against database {db.name!r}. Use `bun test`.")
if "mongomock" in type(db.client).__module__:
    fail("Refusing to run tests against an in-memory mock. Start MongoDB and retry with `bun test`.")

result = None
try:
    suite = unittest.defaultTestLoader.discover(
        str(backend / "apps" / "gavel" / "tests"),
        pattern="test_*.py",
        top_level_dir=str(backend),
    )
    print(f"Running tests against throwaway database {name}.")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
finally:
    try:
        db.client.drop_database(name)
        print(f"Dropped throwaway database {name}.")
    except Exception as exc:
        sys.stderr.write(f"Warning: could not drop throwaway database {name}: {exc}\n")

sys.exit(0 if result is not None and result.wasSuccessful() else 1)
