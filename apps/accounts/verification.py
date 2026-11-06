"""One-time verification challenges and mock-only delivery adapter."""

from collections import deque
from dataclasses import dataclass
from datetime import timedelta
import secrets
from typing import Protocol
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from apps.accounts.models import (
    AccountStatus,
    VerificationChallenge,
    VerificationChannel,
    VerificationPurpose,
    User,
)

CODE_LIFETIME_SECONDS = 10 * 60
MAX_FAILED_ATTEMPTS = 5
SEND_COOLDOWN_SECONDS = 60
MAX_SENDS_PER_HOUR = 3


@dataclass(frozen=True)
class MockVerificationMessage:
    challenge_id: UUID
    purpose: str
    channel: str
    destination: str
    code: str


class VerificationUnavailable(Exception):
    """Raised when this environment has no authorized verification adapter."""


class VerificationRateLimited(Exception):
    """Raised for per-account challenge issue limits."""

    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__("Verification request was rate limited.")


class VerificationProvider(Protocol):
    """Delivery boundary for approved email or phone verification providers."""

    def deliver(
        self,
        *,
        challenge_id: UUID,
        purpose: str,
        channel: str,
        destination: str,
        code: str,
    ) -> None: ...


class MockVerificationProvider:
    """In-memory local/test sink; it never sends or logs a code."""

    def __init__(self):
        self.messages: deque[MockVerificationMessage] = deque(maxlen=100)

    def deliver(
        self,
        *,
        challenge_id: UUID,
        purpose: str,
        channel: str,
        destination: str,
        code: str,
    ) -> None:
        self.messages.append(
            MockVerificationMessage(
                challenge_id=challenge_id,
                purpose=purpose,
                channel=channel,
                destination=destination,
                code=code,
            )
        )

    def clear(self) -> None:
        self.messages.clear()


mock_verification_provider = MockVerificationProvider()


def get_verification_provider() -> VerificationProvider:
    if settings.ALLOW_MOCK_VERIFICATION:
        return mock_verification_provider
    raise VerificationUnavailable("No authorized verification provider is configured.")


def _code_digest(challenge_id: UUID, purpose: str, code: str) -> str:
    payload = f"{challenge_id.hex}:{purpose}:{code}"
    return salted_hmac(
        "apps.accounts.verification",
        payload,
        secret=settings.SECRET_KEY,
        algorithm="sha256",
    ).hexdigest()


def _channel_and_destination(user, purpose: str) -> tuple[str, str]:
    if purpose == VerificationPurpose.PASSWORD_RESET:
        if not user.phone_e164:
            raise VerificationUnavailable("Phone reset is available only for phone accounts.")
        return VerificationChannel.PHONE, user.phone_e164
    if user.email:
        return VerificationChannel.EMAIL, user.email
    if user.phone_e164:
        return VerificationChannel.PHONE, user.phone_e164
    raise VerificationUnavailable("The account has no verification channel.")


def issue_challenge(user: User, purpose: str) -> VerificationChallenge:
    """Create and deliver a bounded one-time challenge for an account."""
    provider = get_verification_provider()
    if purpose not in VerificationPurpose.values:
        raise ValueError("Unsupported verification purpose.")
    code = f"{secrets.randbelow(1_000_000):06d}"
    with transaction.atomic():
        locked_user = User.objects.select_for_update().get(pk=user.pk)
        if purpose == VerificationPurpose.ACCOUNT and locked_user.account_status != AccountStatus.PENDING:
            raise VerificationUnavailable("Only pending accounts can be verified.")
        if purpose == VerificationPurpose.PASSWORD_RESET and not locked_user.is_active:
            raise VerificationUnavailable("Only active accounts can reset a password.")
        if purpose == VerificationPurpose.PASSWORD_RESET and not locked_user.phone_verified_at:
            raise VerificationUnavailable("Phone reset requires a verified phone account.")

        channel, destination = _channel_and_destination(locked_user, purpose)
        now = timezone.now()
        recent = VerificationChallenge.objects.filter(
            user=locked_user,
            purpose=purpose,
            created_at__gte=now - timedelta(hours=1),
        )
        latest = recent.order_by("-created_at").first()
        if latest:
            seconds_since_send = int((now - latest.created_at).total_seconds())
            if seconds_since_send < SEND_COOLDOWN_SECONDS:
                raise VerificationRateLimited(SEND_COOLDOWN_SECONDS - seconds_since_send)
            if recent.count() >= MAX_SENDS_PER_HOUR:
                oldest = recent.order_by("created_at").first()
                retry_after = max(
                    1,
                    int((oldest.created_at + timedelta(hours=1) - now).total_seconds()),
                )
                raise VerificationRateLimited(retry_after)

        VerificationChallenge.objects.select_for_update().filter(
            user=locked_user,
            purpose=purpose,
            consumed_at__isnull=True,
        ).update(consumed_at=now)
        challenge = VerificationChallenge.objects.create(
            user=locked_user,
            purpose=purpose,
            channel=channel,
            code_digest="0" * 64,
            expires_at=now + timedelta(seconds=CODE_LIFETIME_SECONDS),
        )
        challenge.code_digest = _code_digest(challenge.id, purpose, code)
        challenge.save(update_fields=["code_digest"])

    provider.deliver(
        challenge_id=challenge.id,
        purpose=purpose,
        channel=channel,
        destination=destination,
        code=code,
    )
    return challenge


def consume_challenge(user: User, purpose: str, code: str) -> bool:
    """Consume a valid code once, applying account verification atomically."""
    if purpose not in VerificationPurpose.values:
        return False
    now = timezone.now()
    with transaction.atomic():
        locked_user = User.objects.select_for_update().get(pk=user.pk)
        challenge = (
            VerificationChallenge.objects.select_for_update()
            .filter(user=locked_user, purpose=purpose, consumed_at__isnull=True)
            .order_by("-created_at")
            .first()
        )
        if challenge is None:
            return False
        if challenge.expires_at <= now or challenge.failed_attempts >= MAX_FAILED_ATTEMPTS:
            challenge.consumed_at = now
            challenge.save(update_fields=["consumed_at"])
            return False

        expected_digest = _code_digest(challenge.id, purpose, code)
        if not constant_time_compare(challenge.code_digest, expected_digest):
            challenge.failed_attempts += 1
            update_fields = ["failed_attempts"]
            if challenge.failed_attempts >= MAX_FAILED_ATTEMPTS:
                challenge.consumed_at = now
                update_fields.append("consumed_at")
            challenge.save(update_fields=update_fields)
            return False

        challenge.consumed_at = now
        challenge.save(update_fields=["consumed_at"])
        if purpose == VerificationPurpose.ACCOUNT:
            if locked_user.account_status != AccountStatus.PENDING:
                return False
            locked_user.account_status = AccountStatus.ACTIVE
            verified_field = (
                "email_verified_at"
                if challenge.channel == VerificationChannel.EMAIL
                else "phone_verified_at"
            )
            setattr(locked_user, verified_field, now)
            locked_user.save(update_fields=["account_status", verified_field, "updated_at"])
        elif purpose == VerificationPurpose.PASSWORD_RESET:
            if (
                not locked_user.is_active
                or not locked_user.phone_e164
                or not locked_user.phone_verified_at
                or challenge.channel != VerificationChannel.PHONE
            ):
                return False
        return True
