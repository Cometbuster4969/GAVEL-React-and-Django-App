"""Isolated backend suite. Optional --mongo-uri tests a real local MongoDB.

The generated gavel_test_* database is seeded and dropped; application data is
never used. No mock results should be represented as real durability evidence.
"""
import argparse
import os
from pathlib import Path
import sys
import unittest
from uuid import uuid4

parser = argparse.ArgumentParser()
parser.add_argument("--mongo-uri", help="MongoDB host URI (database name will be replaced)")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))
os.environ["DJANGO_SETTINGS_MODULE"] = "calendar_backend.settings"
os.environ["NODE_ENV"] = "development"
os.environ["USE_MONGOMOCK"] = "false" if args.mongo_uri else "true"
from urllib.parse import urlsplit, urlunsplit
uri = urlsplit(args.mongo_uri or "mongodb://127.0.0.1:27017")
name = "gavel_test_" + uuid4().hex
os.environ["MONGODB_URI"] = urlunsplit((uri.scheme, uri.netloc, "/" + name, uri.query, ""))
import django

django.setup()
from mongoengine.connection import get_db
from scripts.seed import seed

db = get_db()
if args.mongo_uri and "mongomock" in type(db.client).__module__:
    raise SystemExit("Real MongoDB requested but unavailable; refusing to report mock results as real.")
try:
    if not db.gavelusers.count_documents({}):
        seed()
    suite = unittest.defaultTestLoader.discover(str(root / "backend" / "apps" / "gavel"), pattern="test_*.py", top_level_dir=str(root / "backend"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
finally:
    db.client.drop_database(name)
sys.exit(0 if result.wasSuccessful() else 1)
