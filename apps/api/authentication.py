"""Database-backed Bearer authentication with expiry and revocation checks."""

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from apps.accounts.models import AccountStatus
from apps.api.models import ApiAccessToken
from apps.api.token_services import digest_token


class BearerTokenAuthentication(BaseAuthentication):
    keyword = b"bearer"

    def authenticate(self, request):
        parts = get_authorization_header(request).split()
        if not parts:
            return None
        if parts[0].lower() != self.keyword:
            return None
        if len(parts) != 2:
            raise AuthenticationFailed("Invalid bearer credentials.")
        try:
            raw_token = parts[1].decode("utf-8")
        except UnicodeError as error:
            raise AuthenticationFailed("Invalid bearer credentials.") from error
        token = ApiAccessToken.objects.select_related("user").filter(
            token_digest=digest_token(raw_token),
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
            user__account_status=AccountStatus.ACTIVE,
        ).first()
        if token is None:
            raise AuthenticationFailed("Invalid or expired bearer credentials.")
        return token.user, token

    def authenticate_header(self, request):
        return "Bearer"
