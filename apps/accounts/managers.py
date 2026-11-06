"""User creation helpers enforcing the one-identifier account policy."""

from django.contrib.auth.base_user import BaseUserManager
from django.core.exceptions import ValidationError


class UserManager(BaseUserManager):
    use_in_migrations = True

    @classmethod
    def normalize_email_identifier(cls, email: str | None) -> str | None:
        """Treat email identifiers case-insensitively and trim whitespace."""
        if not email:
            return None
        return cls.normalize_email(email.strip()).casefold()

    @staticmethod
    def normalize_phone_identifier(phone_e164: str | None) -> str | None:
        if not phone_e164:
            return None
        return phone_e164.strip()

    def create_user(
        self,
        email: str | None = None,
        phone_e164: str | None = None,
        password: str | None = None,
        **extra_fields,
    ):
        email = self.normalize_email_identifier(email)
        phone_e164 = self.normalize_phone_identifier(phone_e164)
        if bool(email) == bool(phone_e164):
            raise ValueError("Provide exactly one login identifier: email or phone_e164.")
        requested_status = extra_fields.pop("account_status", "PENDING")
        if requested_status != "PENDING":
            raise ValueError("New user accounts must remain PENDING until a verification flow activates them.")
        return self._create_user(email, phone_e164, password, "PENDING", extra_fields)

    def _create_user(self, email, phone_e164, password, account_status, extra_fields):
        extra_fields["account_status"] = account_status
        user = self.model(email=email, phone_e164=phone_e164, **extra_fields)
        if password is None:
            user.set_unusable_password()
        else:
            user.set_password(password)
        user.full_clean()
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        **extra_fields,
    ):
        if not email:
            raise ValueError("A superuser must have an email login identifier.")
        if extra_fields.pop("phone_e164", None):
            raise ValueError("Superuser creation uses the email login path.")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("account_status", "ACTIVE")
        if extra_fields.get("is_staff") is not True:
            raise ValueError("A superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("A superuser must have is_superuser=True.")
        extra_fields.pop("account_status", None)
        return self._create_user(email, None, password, "ACTIVE", extra_fields)
