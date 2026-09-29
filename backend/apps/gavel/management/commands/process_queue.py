from django.core.management.base import BaseCommand

from apps.gavel.jobs import process_next_job


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
        return process_next_job(limit)
