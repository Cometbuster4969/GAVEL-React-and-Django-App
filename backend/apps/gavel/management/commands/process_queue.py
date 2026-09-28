from datetime import datetime, timezone

from django.core.management.base import BaseCommand
from mongoengine import Q
from pymongo import ReturnDocument

from apps.gavel.models import ProcessingJob
from apps.gavel.services import process_submissions


class Command(BaseCommand):
    help = "Process queued Gavel submissions independently of an API request."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Process available jobs once and exit.")
        parser.add_argument("--sleep", type=float, default=2, help="Polling interval in seconds.")
        parser.add_argument("--limit", type=int, default=25, help="Maximum submissions per claimed job.")

    def handle(self, *args, **options):
        while True:
            processed = self.process_available(options["limit"])
            if options["once"]:
                self.stdout.write(f"Processed {processed} queue job(s).")
                return
            if not processed:
                import time

                time.sleep(max(options["sleep"], 0.1))

    def process_available(self, limit):
        processed = 0
        now = datetime.now(timezone.utc)
        job = ProcessingJob._get_collection().find_one_and_update(
            {"status": "queued", "availableAt": {"$lte": now}},
            {"$set": {"status": "running", "lockedAt": now}, "$inc": {"attempts": 1}},
            sort=[("availableAt", 1), ("_id", 1)],
            return_document=ReturnDocument.AFTER,
        )
        if job is None:
            return 0
        try:
            process_submissions(None, str(job["campaignId"]), limit)
            ProcessingJob._get_collection().update_one(
                {"_id": job["_id"], "status": "running"},
                {"$set": {"status": "completed", "updatedAt": datetime.now(timezone.utc)}},
            )
        except Exception as error:
            ProcessingJob._get_collection().update_one(
                {"_id": job["_id"], "status": "running"},
                {"$set": {"status": "failed", "error": str(error)[:500], "updatedAt": datetime.now(timezone.utc)}},
            )
        return 1