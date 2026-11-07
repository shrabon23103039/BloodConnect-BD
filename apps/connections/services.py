"""Atomic contact request creation and state transitions."""

from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import AccountStatus
from apps.connections.models import (
    Connection,
    ConnectionStatus,
    ContactRequest,
    ContactRequestStatus,
)
from apps.donors.models import DonorProfile
from apps.requests.models import BloodRequest, BloodRequestStatus
from apps.donors.services import has_current_contact_consent
from apps.audit.services import record_audit_event
from apps.notifications.models import NotificationType
from apps.notifications.services import notify_contact_event
from apps.moderation.services import is_blocked_between
from apps.donors.services import has_current_contact_consent

CONTACT_REQUEST_TTL = timedelta(hours=48)


def _active_user(user):
    if not user.is_authenticated or user.account_status != AccountStatus.ACTIVE:
        raise PermissionDenied("An active account is required.")
    return user.__class__.objects.select_for_update().get(pk=user.pk)


@transaction.atomic
def create_contact_request(*, recipient, donor_profile_id, blood_request_id, message="", now=None):
    """Create one pending request for an active recipient and discoverable donor."""
    now = now or timezone.now()
    recipient = _active_user(recipient)
    try:
        donor = DonorProfile.objects.discoverable().select_for_update().get(
            pk=donor_profile_id
        )
    except DonorProfile.DoesNotExist as error:
        raise ValidationError("This donor is not currently accepting contact requests.") from error
    if donor.user_id == recipient.pk:
        raise ValidationError("You cannot contact your own donor profile.")
    if is_blocked_between(user_a=recipient, user_b=donor.user):
        raise ValidationError("This profile is not available for contact requests.")
    try:
        blood_request = BloodRequest.objects.select_for_update().get(
            pk=blood_request_id,
            requester=recipient,
            status=BloodRequestStatus.OPEN,
            expires_at__gt=now,
        )
    except BloodRequest.DoesNotExist as error:
        raise ValidationError("Choose one of your open, current blood requests.") from error

    existing = ContactRequest.objects.filter(
        recipient=recipient,
        donor_profile=donor,
        blood_request=blood_request,
        status=ContactRequestStatus.PENDING,
    ).first()
    if existing:
        raise ValidationError("A contact request is already pending for this donor and request.")

    expires_at = min(now + CONTACT_REQUEST_TTL, blood_request.expires_at)
    if expires_at <= now:
        raise ValidationError("This blood request is no longer accepting contact requests.")

    try:
        # Keep the savepoint so a concurrent insert can be translated to the
        # same user-facing duplicate error without breaking the outer transaction.
        with transaction.atomic():
            contact_request = ContactRequest.objects.create(
                recipient=recipient,
                donor_profile=donor,
                blood_request=blood_request,
                message=message.strip() or None,
                status=ContactRequestStatus.PENDING,
                expires_at=expires_at,
            )
            notify_contact_event(
                recipient=donor.user,
                notification_type=NotificationType.CONTACT_REQUEST_RECEIVED,
                contact_request_id=contact_request.pk,
            )
            record_audit_event(
                actor=recipient,
                action="contact_request.created",
                resource_type="contact_request",
                resource_id=contact_request.pk,
                metadata={"to_status": ContactRequestStatus.PENDING, "reason_code": "RECIPIENT_REQUEST"},
            )
            return contact_request
    except IntegrityError as error:
        raise ValidationError(
            "A contact request is already pending for this donor and request."
        ) from error


@transaction.atomic
def transition_contact_request(*, user, contact_request_id, target_status, now=None):
    """Apply an authorized pending-state decision while holding row locks."""
    if target_status not in ContactRequestStatus.values:
        raise ValidationError({"status": "Select a supported contact request state."})
    if target_status in (ContactRequestStatus.PENDING, ContactRequestStatus.EXPIRED):
        raise ValidationError("This contact request state cannot be selected here.")
    actor = _active_user(user)
    try:
        request = ContactRequest.objects.select_for_update().select_related(
            "donor_profile"
        ).get(pk=contact_request_id)
    except ContactRequest.DoesNotExist as error:
        raise PermissionDenied("You may only change a contact request addressed to you.") from error

    if target_status == ContactRequestStatus.CANCELLED:
        if request.recipient_id != actor.pk:
            raise PermissionDenied("Only the recipient may cancel this contact request.")
    elif target_status in (ContactRequestStatus.ACCEPTED, ContactRequestStatus.DECLINED):
        if request.donor_profile.user_id != actor.pk:
            raise PermissionDenied("Only the addressed donor may decide this request.")
    else:
        raise ValidationError("This contact request state transition is not allowed.")

    if request.status == target_status:
        return request
    if request.status != ContactRequestStatus.PENDING:
        raise ValidationError("This contact request is already closed.")

    now = now or timezone.now()
    previous_status = request.status
    if request.expires_at <= now:
        request.status = ContactRequestStatus.EXPIRED
    else:
        request.status = target_status
    request.decided_at = now
    request.save(update_fields=["status", "decided_at", "updated_at"])
    record_audit_event(
        actor=actor,
        action="contact_request.transitioned",
        resource_type="contact_request",
        resource_id=request.pk,
        metadata={
            "from_status": previous_status,
            "to_status": request.status,
            "reason_code": "EXPIRED_BEFORE_DECISION" if request.status == ContactRequestStatus.EXPIRED else "PARTICIPANT_ACTION",
        },
    )
    if request.status == ContactRequestStatus.ACCEPTED:
        Connection.objects.get_or_create(contact_request=request)
        notify_contact_event(
            recipient=request.recipient,
            notification_type=NotificationType.CONTACT_REQUEST_ACCEPTED,
            contact_request_id=request.pk,
        )
    elif request.status == ContactRequestStatus.DECLINED:
        notify_contact_event(
            recipient=request.recipient,
            notification_type=NotificationType.CONTACT_REQUEST_DECLINED,
            contact_request_id=request.pk,
        )
    elif request.status == ContactRequestStatus.CANCELLED:
        notify_contact_event(
            recipient=request.donor_profile.user,
            notification_type=NotificationType.CONTACT_REQUEST_CANCELLED,
            contact_request_id=request.pk,
        )
    elif request.status == ContactRequestStatus.EXPIRED:
        notify_contact_event(
            recipient=request.recipient,
            notification_type=NotificationType.CONTACT_REQUEST_EXPIRED,
            contact_request_id=request.pk,
        )
    return request


@transaction.atomic
def get_disclosed_contact_channels(*, recipient, connection_id):
    """Return only donor channels consented to for this recipient's accepted connection."""
    recipient = _active_user(recipient)
    try:
        connection = Connection.objects.select_for_update().select_related(
            "contact_request"
        ).get(
            pk=connection_id,
            contact_request__recipient=recipient,
        )
    except Connection.DoesNotExist as error:
        raise PermissionDenied("You may only view your accepted connections.") from error
    contact_request = connection.contact_request
    if (
        contact_request.status != ContactRequestStatus.ACCEPTED
        or connection.status != ConnectionStatus.ACTIVE
    ):
        raise PermissionDenied("This connection is not available for contact disclosure.")

    donor_profile = DonorProfile.objects.select_for_update().select_related("user").get(
        pk=contact_request.donor_profile_id
    )
    donor_user = donor_profile.user.__class__.objects.select_for_update().get(
        pk=donor_profile.user_id
    )
    if donor_user.account_status != AccountStatus.ACTIVE:
        return {}
    donor_profile.user = donor_user
    channels = {}
    for channel, field_name in (("phone", "phone_e164"), ("email", "email")):
        if has_current_contact_consent(profile=donor_profile, channel=channel):
            channels[channel] = getattr(donor_user, field_name)
    if channels:
        record_audit_event(
            actor=recipient,
            action="connection.contact_channels.disclosed",
            resource_type="connection",
            resource_id=connection.pk,
            metadata={"to_status": "DISCLOSED", "reason_code": "ACCEPTED_AND_CONSENTED"},
        )
    return channels


@transaction.atomic
def transition_connection(*, user, connection_id, now=None):
    """Close an active connection for either authorized participant."""
    actor = _active_user(user)
    try:
        connection = Connection.objects.select_for_update().select_related(
            "contact_request", "contact_request__donor_profile"
        ).get(pk=connection_id)
    except Connection.DoesNotExist as error:
        raise PermissionDenied("You may only change your own connections.") from error
    contact_request = connection.contact_request
    if not (
        contact_request.recipient_id == actor.pk
        or contact_request.donor_profile.user_id == actor.pk
    ):
        raise PermissionDenied("You may only change your own connections.")
    if connection.status == ConnectionStatus.CLOSED:
        return connection
    if connection.status != ConnectionStatus.ACTIVE:
        raise ValidationError("This connection cannot be closed from its current state.")
    now = now or timezone.now()
    connection.status = ConnectionStatus.CLOSED
    connection.closed_at = now
    connection.save(update_fields=["status", "closed_at"])
    record_audit_event(
        actor=actor,
        action="connection.closed",
        resource_type="connection",
        resource_id=connection.pk,
        metadata={
            "from_status": ConnectionStatus.ACTIVE,
            "to_status": ConnectionStatus.CLOSED,
            "reason_code": "PARTICIPANT_ACTION",
        },
    )
    return connection


def expire_due_contact_requests(*, now=None, batch_size=500):
    """Mark a bounded batch of pending expired contact requests as terminal."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    now = now or timezone.now()
    request_ids = list(
        ContactRequest.objects.filter(
            status=ContactRequestStatus.PENDING,
            expires_at__lte=now,
        )
        .order_by("expires_at", "id")
        .values_list("id", flat=True)[:batch_size]
    )
    expired_count = 0
    for request_id in request_ids:
        with transaction.atomic():
            contact_request = ContactRequest.objects.select_for_update().filter(
                pk=request_id,
                status=ContactRequestStatus.PENDING,
                expires_at__lte=now,
            ).first()
            if contact_request is not None:
                contact_request.status = ContactRequestStatus.EXPIRED
                contact_request.decided_at = now
                contact_request.save(update_fields=["status", "decided_at", "updated_at"])
                notify_contact_event(
                    recipient=contact_request.recipient,
                    notification_type=NotificationType.CONTACT_REQUEST_EXPIRED,
                    contact_request_id=contact_request.pk,
                )
                expired_count += 1
    return expired_count
