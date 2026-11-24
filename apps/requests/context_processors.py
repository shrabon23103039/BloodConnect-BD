"""Expose owner-scoped counts for the authenticated request workspace."""

from django.db.models import Count, Q
from django.http import HttpRequest


def request_workspace_counts(request: HttpRequest) -> dict[str, int]:
    user = getattr(request, "user", None)
    match = getattr(request, "resolver_match", None)
    if (
        not user
        or not user.is_authenticated
        or not match
        or match.namespace not in {"requests", "connections"}
        or match.url_name not in {"list", "incoming", "outgoing"}
    ):
        return {}

    from apps.connections.models import ContactRequest
    from apps.requests.models import BloodRequest

    contact_counts = ContactRequest.objects.filter(
        Q(recipient_id=user.pk) | Q(donor_profile__user_id=user.pk)
    ).aggregate(
        incoming=Count("pk", filter=Q(donor_profile__user_id=user.pk)),
        outgoing=Count("pk", filter=Q(recipient_id=user.pk)),
    )
    return {
        "my_blood_request_count": BloodRequest.objects.filter(
            requester_id=user.pk
        ).count(),
        "incoming_contact_request_count": contact_counts["incoming"],
        "outgoing_contact_request_count": contact_counts["outgoing"],
    }
