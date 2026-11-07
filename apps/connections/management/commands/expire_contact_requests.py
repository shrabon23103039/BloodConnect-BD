from django.core.management.base import BaseCommand, CommandError

from apps.connections.services import expire_due_contact_requests


class Command(BaseCommand):
    help = "Expire due pending contact requests in a bounded batch."

    def add_arguments(self, parser):
        parser.add_argument("--batch-size", type=int, default=500)

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        if batch_size < 1:
            raise CommandError("--batch-size must be at least 1")
        expired = expire_due_contact_requests(batch_size=batch_size)
        self.stdout.write(f"Expired {expired} contact request(s).")
