"""Custom account model. Donor and health profiles live in separate apps."""

import uuid

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from .managers import UserManager


class AccountStatus(models.TextChoices):
    PENDING = "PENDING", "Pending verification"
    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"
    DEACTIVATED = "DEACTIVATED", "Deactivated"


phone_e164_validator = RegexValidator(
    regex=r"^\+[1-9][0-9]{1,14}$",
    message="Enter a phone number in E.164 format, including the leading + and country code.",
)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=254, null=True, blank=True, unique=True)
    phone_e164 = models.CharField(
        max_length=16,
        null=True,
        blank=True,
        unique=True,
        validators=[phone_e164_validator],
    )
    display_name = models.CharField(max_length=120)
    account_status = models.CharField(
        max_length=20,
        choices=AccountStatus.choices,
        default=AccountStatus.PENDING,
        db_index=True,
    )
    is_staff = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    phone_verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["display_name"]

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(email__isnull=False, phone_e164__isnull=True)
                    | models.Q(email__isnull=True, phone_e164__isnull=False)
                ),
                name="accounts_user_exactly_one_identifier",
            ),
            models.UniqueConstraint(
                Lower("email"),
                condition=models.Q(email__isnull=False),
                name="accounts_user_email_lower_uniq",
            ),
        ]

    def clean(self):
        # AbstractBaseUser.clean normalizes USERNAME_FIELD using get_username;
        # that would copy a phone-only username into the nullable email field.
        self.email = UserManager.normalize_email_identifier(self.email)
        self.phone_e164 = UserManager.normalize_phone_identifier(self.phone_e164)
        self.display_name = self.display_name.strip()
        if bool(self.email) == bool(self.phone_e164):
            raise ValidationError("Provide exactly one login identifier: email or phone_e164.")

    def save(self, *args, **kwargs):
        self.email = UserManager.normalize_email_identifier(self.email)
        self.phone_e164 = UserManager.normalize_phone_identifier(self.phone_e164)
        self.display_name = self.display_name.strip()
        return super().save(*args, **kwargs)

    @property
    def is_active(self) -> bool:
        """Only verified/activated accounts can authenticate."""
        return self.account_status == AccountStatus.ACTIVE

    def get_username(self) -> str:
        return self.email or self.phone_e164 or ""

    def get_full_name(self) -> str:
        return self.display_name

    def get_short_name(self) -> str:
        return self.display_name

    def __str__(self) -> str:
        return self.display_name
