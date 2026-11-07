"""Privacy-protective global operational counters."""

from apps.connections.models import ContactRequest, ContactRequestStatus
from apps.donors.models import DonorProfile
from apps.moderation.models import ReportStatus, UserReport
from apps.requests.models import BloodRequest, BloodRequestStatus

MINIMUM_REPORTING_CELL = 5


def suppress_small_count(value):
    """Hide zero and low counts so a dashboard cannot reveal individual activity."""
    return value if value >= MINIMUM_REPORTING_CELL else None


def get_operational_metrics():
    """Return fixed, global counts only; never return dimensions or source rows."""
    counts = {
        "discoverable_donors": DonorProfile.objects.discoverable().count(),
        "open_blood_requests": BloodRequest.objects.filter(
            status=BloodRequestStatus.OPEN,
            public_listing_enabled=True,
        ).count(),
        "pending_contact_requests": ContactRequest.objects.filter(
            status=ContactRequestStatus.PENDING
        ).count(),
        "open_reports": UserReport.objects.filter(status=ReportStatus.OPEN).count(),
    }
    return {name: suppress_small_count(value) for name, value in counts.items()}
