"""Authentication backend for the account's single email or phone identifier."""

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

from apps.accounts.managers import UserManager


class IdentifierBackend(ModelBackend):
    """Authenticate active users by normalized email or E.164 phone number."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = username or kwargs.get("email") or kwargs.get("phone_e164")
        if not identifier or password is None:
            return None

        identifier = identifier.strip()
        User = get_user_model()
        if "@" in identifier:
            user = User._default_manager.filter(email=UserManager.normalize_email_identifier(identifier)).first()
        else:
            try:
                phone_e164 = UserManager.normalize_phone_identifier(identifier)
                user = User._default_manager.filter(phone_e164=phone_e164).first()
            except (AttributeError, TypeError):
                user = None

        if user is None:
            # Match the password-hash cost for unknown identifiers.
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
