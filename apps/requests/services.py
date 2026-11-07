"""Transactional creation and owner-authorized request lifecycle operations."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_audit_event
from apps.accounts.models import AccountStatus
from apps.requests.models import BloodRequest, BloodRequestStatus

EDITABLE_FIELDS = {
    "blood_group",
    "units_requested",
    "required_at",
    "division",
    "district",
    "upazila",
    "facility_name",
    "facility_address",
    "urgency",
    "description",
    "public_listing_enabled",
    "expires_at",
}


def _active_owner(user):
    if not user.is_authenticated or user.account_status != AccountStatus.ACTIVE:
        raise PermissionDenied("An active account is required.")
    return user.__class__.objects.select_for_update().get(pk=user.pk)


@transaction.atomic
def create_blood_request(*, user, values, publish=False):
    """Create a draft or publish a request owned by an active account."""
    owner = _active_owner(user)
    request_values = {key: value for key, value in values.items() if key in EDITABLE_FIELDS}
    if "required_at" in request_values:
        request_values.setdefault("expires_at", request_values["required_at"])
    blood_request = BloodRequest(requester=owner, **request_values)
    if publish:
        _validate_publish(blood_request)
        blood_request.status = BloodRequestStatus.OPEN
    blood_request.save()
    record_audit_event(
        actor=owner,
        action="blood_request.created",
        resource_type="blood_request",
        resource_id=blood_request.pk,
        metadata={"to_status": blood_request.status, "reason_code": "OWNER_CREATED"},
    )
    return blood_request


def _validate_publish(blood_request, now=None):
    now = now or timezone.now()
    if blood_request.required_at <= now:
        raise ValidationError({"required_at": "Choose a future requested time to publish."})
    if blood_request.expires_at <= now:
        raise ValidationError({"expires_at": "Choose a future expiry time to publish."})
    if blood_request.expires_at < blood_request.required_at:
        raise ValidationError({"expires_at": "Expiry cannot be before the requested time."})


@transaction.atomic
def update_blood_request(*, user, blood_request_id, values):
    """Update an owned draft/open request; never alter lifecycle fields directly."""
    owner = _active_owner(user)
    try:
        request = BloodRequest.objects.select_for_update().get(
            pk=blood_request_id,
            requester=owner,
        )
    except BloodRequest.DoesNotExist as error:
        raise PermissionDenied("You may only update your own blood requests.") from error
    if request.status not in (BloodRequestStatus.DRAFT, BloodRequestStatus.OPEN):
        raise ValidationError("This request can no longer be edited.")
    for field, value in values.items():
        if field not in EDITABLE_FIELDS:
            raise ValidationError({field: "This field cannot be edited here."})
        setattr(request, field, value)
    if request.status == BloodRequestStatus.OPEN:
        _validate_publish(request)
    request.save()
    return request


@transaction.atomic
def transition_blood_request(*, user, blood_request_id, target_status, now=None):
    """Apply owner state changes or due expiration under row locks."""
    if target_status not in BloodRequestStatus.values:
        raise ValidationError({"status": "Select a supported request state."})
    owner = _active_owner(user)
    try:
        request = BloodRequest.objects.select_for_update().get(
            pk=blood_request_id,
            requester=owner,
        )
    except BloodRequest.DoesNotExist as error:
        raise PermissionDenied("You may only change your own blood requests.") from error
    now = now or timezone.now()
    if request.status == target_status:
        return request
    previous_status = request.status
    if request.status == BloodRequestStatus.DRAFT and target_status == BloodRequestStatus.OPEN:
        _validate_publish(request, now=now)
        request.status = BloodRequestStatus.OPEN
        request.save(update_fields=["status", "updated_at"])
        record_audit_event(
            actor=owner,
            action="blood_request.transitioned",
            resource_type="blood_request",
            resource_id=request.pk,
            metadata={"from_status": previous_status, "to_status": request.status, "reason_code": "OWNER_PUBLISHED"},
        )
        return request
    elif request.status != BloodRequestStatus.OPEN:
        raise ValidationError("This request state transition is not allowed.")
    if target_status == BloodRequestStatus.EXPIRED:
        if request.expires_at > now:
            raise ValidationError("A request can expire only after its expiry time.")
    elif target_status not in (BloodRequestStatus.FULFILLED, BloodRequestStatus.CANCELLED):
        raise ValidationError("This request state transition is not allowed.")
    request.status = target_status
    request.save(update_fields=["status", "updated_at"])
    record_audit_event(
        actor=owner,
        action="blood_request.transitioned",
        resource_type="blood_request",
        resource_id=request.pk,
        metadata={
            "from_status": previous_status,
            "to_status": request.status,
            "reason_code": "SYSTEM_EXPIRY" if target_status == BloodRequestStatus.EXPIRED else "OWNER_CLOSED",
        },
    )
    return request


def expire_due_blood_requests(*, now=None, batch_size=500):
    """Expire due open requests in bounded, independently committed batches."""
    now = now or timezone.now()
    ids = list(
        BloodRequest.objects.filter(
            status=BloodRequestStatus.OPEN,
            expires_at__lte=now,
        )
        .order_by("expires_at", "id")
        .values_list("id", flat=True)[:batch_size]
    )
    expired = 0
    for request_id in ids:
        with transaction.atomic():
            request = BloodRequest.objects.select_for_update().filter(
                pk=request_id,
                status=BloodRequestStatus.OPEN,
                expires_at__lte=now,
            ).first()
            if request is not None:
                request.status = BloodRequestStatus.EXPIRED
                request.save(update_fields=["status", "updated_at"])
                expired += 1
    return expired
