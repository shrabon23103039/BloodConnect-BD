"""Owner-scoped donor profile writes and lifecycle transitions."""

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import AccountStatus
from apps.accounts.permissions import AccountRole, has_role
from apps.donors.models import (
    AvailabilityStatus,
    DonorProfile,
    DonorProfileStatus,
)
from apps.governance.models import (
    ConsentSource,
    ConsentType,
    current_consent_state,
    record_consent,
)


def _lock_active_owner(user):
    if not has_role(user, AccountRole.AUTHENTICATED_USER):
        raise PermissionDenied("An active account is required.")
    locked_user = user.__class__.objects.select_for_update().get(pk=user.pk)
    if locked_user.account_status != AccountStatus.ACTIVE:
        raise PermissionDenied("An active account is required.")
    return locked_user


def has_current_contact_consent(*, profile, channel):
    """Check stored preference and current ledger state; this alone is not disclosure authorization."""
    fields = {
        "phone": (
            profile.share_phone_after_accept,
            ConsentType.PHONE_SHARE_AFTER_ACCEPT,
            profile.user.phone_e164,
            profile.user.phone_verified_at,
        ),
        "email": (
            profile.share_email_after_accept,
            ConsentType.EMAIL_SHARE_AFTER_ACCEPT,
            profile.user.email,
            profile.user.email_verified_at,
        ),
    }
    if channel not in fields:
        return False
    enabled, consent_type, identifier, verified_at = fields[channel]
    return bool(
        enabled
        and identifier
        and verified_at
        and current_consent_state(profile.user).get(consent_type, False)
    )


@transaction.atomic
def save_donor_profile(*, user, profile, values, consent_fields):
    """Create or update only the active account's own profile and consent state."""
    locked_user = _lock_active_owner(user)
    if not profile._state.adding:
        try:
            profile = DonorProfile.objects.select_for_update().get(
                pk=profile.pk,
                user=locked_user,
            )
        except DonorProfile.DoesNotExist as error:
            raise PermissionDenied("You may only update your own donor profile.") from error
    else:
        profile.user = locked_user

    for field in (
        "blood_group",
        "division",
        "district",
        "upazila",
        "public_alias",
        "preferred_contact_method",
        "last_donation_date",
    ):
        setattr(profile, field, values[field])

    for field, consent_type, identifier, verified_at in (
        (
            "share_phone_after_accept",
            ConsentType.PHONE_SHARE_AFTER_ACCEPT,
            locked_user.phone_e164,
            locked_user.phone_verified_at,
        ),
        (
            "share_email_after_accept",
            ConsentType.EMAIL_SHARE_AFTER_ACCEPT,
            locked_user.email,
            locked_user.email_verified_at,
        ),
    ):
        if field not in consent_fields:
            continue
        granted = bool(values.get(field))
        if granted and (not identifier or not verified_at):
            raise ValidationError({field: "Only a verified contact method can be shared."})
        setattr(profile, field, granted)

    profile.save()
    for field, consent_type in (
        ("share_phone_after_accept", ConsentType.PHONE_SHARE_AFTER_ACCEPT),
        ("share_email_after_accept", ConsentType.EMAIL_SHARE_AFTER_ACCEPT),
    ):
        if field in consent_fields:
            record_consent(
                user=locked_user,
                consent_type=consent_type,
                policy_version=settings.PRIVACY_POLICY_VERSION,
                granted=bool(values.get(field)),
                source=ConsentSource.WEB,
            )
    return profile


@transaction.atomic
def pause_donor_profile(*, user, profile):
    locked_user = _lock_active_owner(user)
    try:
        profile = DonorProfile.objects.select_for_update().get(pk=profile.pk, user=locked_user)
    except DonorProfile.DoesNotExist as error:
        raise PermissionDenied("You may only pause your own donor profile.") from error
    profile.availability_status = AvailabilityStatus.PAUSED
    profile.availability_updated_at = timezone.now()
    profile.save(update_fields=["availability_status", "availability_updated_at", "updated_at"])
    return profile


@transaction.atomic
def deactivate_donor_profile(*, user, profile):
    locked_user = _lock_active_owner(user)
    try:
        profile = DonorProfile.objects.select_for_update().get(pk=profile.pk, user=locked_user)
    except DonorProfile.DoesNotExist as error:
        raise PermissionDenied("You may only deactivate your own donor profile.") from error
    profile.profile_status = DonorProfileStatus.HIDDEN
    profile.visibility_enabled = False
    profile.availability_status = AvailabilityStatus.UNAVAILABLE
    profile.availability_updated_at = timezone.now()
    profile.save(
        update_fields=[
            "profile_status",
            "visibility_enabled",
            "availability_status",
            "availability_updated_at",
            "updated_at",
        ]
    )
    record_consent(
        user=locked_user,
        consent_type=ConsentType.DONOR_DISCOVERY,
        policy_version=settings.PRIVACY_POLICY_VERSION,
        granted=False,
        source=ConsentSource.WEB,
    )
    return profile
