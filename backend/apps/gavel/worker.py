"""Standalone Gavel worker: queued submission jobs plus the audit outbox.

Run it next to the API in any deployment shape:

```bash
bun run worker              # from the repository root
.venv/bin/python -m apps.gavel.worker --once    # from backend/
```

The management commands (``process_queue``, ``drain_audit_outbox``) cover the
same work when Django's app registry is fully loaded (a real MongoDB
deployment). This entry point imports the domain modules directly, so it also
works in the in-memory mongomock fallback where settings auto-seeding runs
before ``INSTALLED_APPS`` is applied and app-config discovery is unavailable.
"""

import argparse
import os
import sys
import time


def bootstrap():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "calendar_backend.settings")
    import django

    django.setup()


def run_pass(limit=25, max_attempts=5):
    from apps.gavel.jobs import process_next_job
    from apps.gavel.services import drain_audit_outbox

    processed = 0
    while process_next_job(limit):
        processed += 1
    stats = drain_audit_outbox(limit=limit, max_attempts=max_attempts)
    return processed, stats


def main(argv=None):
    parser = argparse.ArgumentParser(description="Process Gavel submission jobs and drain the audit outbox.")
    parser.add_argument("--once", action="store_true", help="Run one pass and exit.")
    parser.add_argument("--sleep", type=float, default=2, help="Polling interval in seconds.")
    parser.add_argument("--limit", type=int, default=25, help="Maximum submissions per job / outbox entries per pass.")
    parser.add_argument("--max-attempts", type=int, default=5, help="Audit outbox attempts before dead-lettering.")
    options = parser.parse_args(argv)

    bootstrap()
    while True:
        processed, stats = run_pass(limit=options.limit, max_attempts=options.max_attempts)
        if processed or stats["scanned"]:
            print(
                "Worker pass: processed {processed} job(s); audit outbox delivered {delivered}, "
                "retried {retried}, failed {failed}, pending {pending}.".format(processed=processed, **stats),
                flush=True,
            )
        if options.once:
            return 0
        if not processed and not stats["scanned"]:
            time.sleep(max(options.sleep, 0.1))


if __name__ == "__main__":
    sys.exit(main())
