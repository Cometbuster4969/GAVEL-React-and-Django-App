"""Operator-only identity configuration; no self-service group manipulation."""
from django.core.management.base import BaseCommand, CommandError
from apps.gavel import repository
from apps.gavel.models import GavelUser, ReviewAssignment


class Command(BaseCommand):
    help = "Assign a verified independence group to an account (maintenance window only)."

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("group", help="Stable verified person/team group; aliases must use the same group.")

    def handle(self, *args, **options):
        user = repository.find_user_by_email(options["email"])
        if user is None:
            raise CommandError("Active account not found.")
        group = options["group"].strip().casefold()
        if not group or len(group) > 120:
            raise CommandError("Group must be 1–120 characters.")
        if ReviewAssignment.objects(reviewer_id=user.id).count():
            raise CommandError("Identity already has review history. Resolve identity merges with an audited data migration; do not relabel historical votes.")
        updated = GavelUser.objects(id=user.id, review_identity_locked__ne=True).modify(set__independence_group=group, new=True)
        if updated is None:
            raise CommandError("Review identity is locked by a claim. Use an audited identity migration.")
        self.stdout.write("Verified independence group configured. Undeclared relationships cannot be inferred automatically.")
