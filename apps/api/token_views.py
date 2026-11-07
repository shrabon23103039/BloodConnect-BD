"""Rate-limited API token issue, refresh and revocation endpoints."""

from django.contrib.auth import authenticate
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.accounts.models import AccountStatus
from apps.accounts.throttling import limited_by_ip
from apps.api.authentication import BearerTokenAuthentication
from apps.api.serializers import (
    RefreshTokenSerializer,
    TokenObtainSerializer,
    TokenPairSerializer,
)
from apps.api.token_services import issue_token_pair, revoke_refresh_token, rotate_refresh_token


class _PublicTokenView(APIView):
    authentication_classes = [BearerTokenAuthentication]
    permission_classes = [AllowAny]


class ObtainTokenView(_PublicTokenView):
    @extend_schema(
        request=TokenObtainSerializer,
        responses={200: TokenPairSerializer, 401: None},
    )
    @method_decorator(limited_by_ip(scope="api-token-issue", limit=10, window_seconds=60, api_response=True))
    def post(self, request):
        serializer = TokenObtainSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data["identifier"],
            password=serializer.validated_data["password"],
        )
        if user is None or user.account_status != AccountStatus.ACTIVE:
            raise AuthenticationFailed("Invalid credentials.")
        tokens = issue_token_pair(user=user)
        return Response(tokens, status=status.HTTP_200_OK)


class RefreshTokenView(_PublicTokenView):
    @extend_schema(
        request=RefreshTokenSerializer,
        responses={200: TokenPairSerializer, 401: None},
    )
    @method_decorator(limited_by_ip(scope="api-token-refresh", limit=30, window_seconds=60, api_response=True))
    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tokens = rotate_refresh_token(raw_token=serializer.validated_data["refresh_token"])
        if tokens is None:
            raise AuthenticationFailed("Invalid or expired refresh token.")
        return Response(tokens, status=status.HTTP_200_OK)


class RevokeTokenView(_PublicTokenView):
    @extend_schema(request=RefreshTokenSerializer, responses={204: None})
    @method_decorator(limited_by_ip(scope="api-token-revoke", limit=30, window_seconds=60, api_response=True))
    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        revoke_refresh_token(raw_token=serializer.validated_data["refresh_token"])
        return Response(status=status.HTTP_204_NO_CONTENT)
