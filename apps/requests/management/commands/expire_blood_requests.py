from django.core.management.base import BaseCommand

from apps.requests.services import expire_due_blood_requests


class Command(BaseCommand):
    help = "Mark due open blood requests as expired."

    def handle(self, *args, **options):
        count = expire_due_blood_requests()
        self.stdout.write(f"Expired {count} blood request(s).")
