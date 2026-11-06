"""Remove expired verification metadata after a short retention window."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import VerificationChallenge


class Command(BaseCommand):
    help = "Purge verification challenge records expired for more than 24 hours."

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(hours=24)
        deleted_count, _ = VerificationChallenge.objects.filter(
            expires_at__lt=cutoff
        ).delete()
        self.stdout.write(f"Purged {deleted_count} expired verification challenge records.")
