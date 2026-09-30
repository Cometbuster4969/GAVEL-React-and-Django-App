from django.apps import AppConfig


class GavelConfig(AppConfig):
    name = "apps.gavel"

    def ready(self):
        # Seed only the explicitly development-only, process-local mock store.
        # Never call django.setup() while settings are being imported: doing so
        # freezes an empty app registry and hides management commands.
        from mongoengine.connection import get_db
        db = get_db()
        if "mongomock" in type(db.client).__module__ and not db.gavelusers.count_documents({}):
            from scripts.seed import seed
            seed()
