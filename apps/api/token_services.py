"""Issue and rotate short-lived, opaque API bearer tokens."""

import hashlib
import secrets
import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import AccountStatus
from apps.audit.services import record_audit_event
from apps.api.models import ApiAccessToken, ApiRefreshToken

ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=30)
# B105 is suppressed because this literal names the HTTP auth scheme, not a secret.
BEARER_SCHEME = "Bearer"  # nosec B105


def digest_token(raw_token):
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _new_secret():
    return secrets.token_urlsafe(32)


def _issue_pair(*, user, family_id=None, now=None):
    now = now or timezone.now()
    family_id = family_id or uuid.uuid4()
    access_token = _new_secret()
    refresh_token = _new_secret()
    ApiAccessToken.objects.create(
        user=user,
        token_digest=digest_token(access_token),
        family_id=family_id,
        expires_at=now + ACCESS_TOKEN_TTL,
    )
    ApiRefreshToken.objects.create(
        user=user,
        token_digest=digest_token(refresh_token),
        family_id=family_id,
        expires_at=now + REFRESH_TOKEN_TTL,
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": BEARER_SCHEME,
        "expires_in": int(ACCESS_TOKEN_TTL.total_seconds()),
    }


@transaction.atomic
def issue_token_pair(*, user, now=None):
    locked_user = get_user_model().objects.select_for_update().get(pk=user.pk)
    if locked_user.account_status != AccountStatus.ACTIVE:
        return None
    tokens = _issue_pair(user=locked_user, now=now)
    access = ApiAccessToken.objects.get(token_digest=digest_token(tokens["access_token"]))
    record_audit_event(
        actor=locked_user,
        action="api.token.issued",
        resource_type="api_token_family",
        resource_id=access.family_id,
        metadata={"to_status": "ACTIVE", "reason_code": "PASSWORD_AUTH"},
    )
    return tokens


def _revoke_family(*, user_id, family_id, now):
    ApiRefreshToken.objects.filter(
        user_id=user_id, family_id=family_id, revoked_at__isnull=True
    ).update(revoked_at=now)
    ApiAccessToken.objects.filter(
        user_id=user_id, family_id=family_id, revoked_at__isnull=True
    ).update(revoked_at=now)


@transaction.atomic
def revoke_user_tokens(*, user, now=None):
    """Revoke every active API token family after a credential reset."""
    now = now or timezone.now()
    family_ids = set(
        ApiAccessToken.objects.filter(
            user_id=user.pk, revoked_at__isnull=True
        ).values_list("family_id", flat=True)
    )
    family_ids.update(
        ApiRefreshToken.objects.filter(
            user_id=user.pk, revoked_at__isnull=True
        ).values_list("family_id", flat=True)
    )
    ApiAccessToken.objects.filter(
        user_id=user.pk, revoked_at__isnull=True
    ).update(revoked_at=now)
    ApiRefreshToken.objects.filter(
        user_id=user.pk, revoked_at__isnull=True
    ).update(revoked_at=now)
    for family_id in family_ids:
        record_audit_event(
            actor=user,
            action="api.token.revoked",
            resource_type="api_token_family",
            resource_id=family_id,
            metadata={"to_status": "REVOKED", "reason_code": "PASSWORD_RESET"},
        )
@transaction.atomic
def rotate_refresh_token(*, raw_token, now=None):
    """Consume one refresh token; reuse revokes every token in its family."""
    now = now or timezone.now()
    try:
        token = ApiRefreshToken.objects.select_for_update().select_related("user").get(
            token_digest=digest_token(raw_token)
        )
    except ApiRefreshToken.DoesNotExist:
        return None
    if token.used_at is not None:
        _revoke_family(user_id=token.user_id, family_id=token.family_id, now=now)
        record_audit_event(
            actor=token.user,
            action="api.token.replay_detected",
            resource_type="api_token_family",
            resource_id=token.family_id,
            metadata={"to_status": "REVOKED", "reason_code": "REFRESH_REUSE"},
        )
        return None
    if token.revoked_at is not None or token.expires_at <= now:
        return None
    if token.user.account_status != AccountStatus.ACTIVE:
        _revoke_family(user_id=token.user_id, family_id=token.family_id, now=now)
        return None

    token.used_at = now
    token.save(update_fields=["used_at"])
    ApiAccessToken.objects.filter(
        user_id=token.user_id,
        family_id=token.family_id,
        revoked_at__isnull=True,
    ).update(revoked_at=now)
    tokens = _issue_pair(user=token.user, family_id=token.family_id, now=now)
    record_audit_event(
        actor=token.user,
        action="api.token.rotated",
        resource_type="api_token_family",
        resource_id=token.family_id,
        metadata={"to_status": "ACTIVE", "reason_code": "REFRESH_ROTATION"},
    )
    return tokens


@transaction.atomic
def revoke_refresh_token(*, raw_token, now=None):
    now = now or timezone.now()
    token = ApiRefreshToken.objects.select_for_update().filter(
        token_digest=digest_token(raw_token)
    ).first()
    if token is None:
        return False
    _revoke_family(user_id=token.user_id, family_id=token.family_id, now=now)
    record_audit_event(
        actor=token.user,
        action="api.token.revoked",
        resource_type="api_token_family",
        resource_id=token.family_id,
        metadata={"to_status": "REVOKED", "reason_code": "CLIENT_LOGOUT"},
    )
    return True
