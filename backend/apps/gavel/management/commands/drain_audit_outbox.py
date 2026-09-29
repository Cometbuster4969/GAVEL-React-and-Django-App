from django.core.management.base import BaseCommand

from apps.gavel.services import drain_audit_outbox


class Command(BaseCommand):
    help = "Deliver durable audit-outbox entries into the audit history with bounded retries."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Drain the available entries once and exit.")
        parser.add_argument("--sleep", type=float, default=2, help="Polling interval in seconds.")
        parser.add_argument("--limit", type=int, default=25, help="Maximum entries delivered per pass.")
        parser.add_argument("--max-attempts", type=int, default=5, help="Attempts before an entry is dead-lettered.")

    def handle(self, *args, **options):
        while True:
            stats = drain_audit_outbox(limit=options["limit"], max_attempts=options["max_attempts"])
            if options["once"]:
                self.stdout.write(
                    "Audit outbox: delivered {delivered}, retried {retried}, failed {failed}, "
                    "pending {pending} (scanned {scanned}).".format(**stats)
                )
                return
            if not stats["scanned"]:
                import time

                time.sleep(max(options["sleep"], 0.1))
