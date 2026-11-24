from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APIRequestFactory

from apps.api.serializers import (
    BloodRequestReadSerializer,
    ContactRequestReadSerializer,
    DonorSearchSerializer,
)
from apps.api.authentication import BearerTokenAuthentication
from apps.api.models import ApiAccessToken, ApiRefreshToken
from apps.api.token_services import digest_token, issue_token_pair
from apps.accounts.models import AccountStatus
from rest_framework.exceptions import AuthenticationFailed


class ApiBaselineTests(SimpleTestCase):
    def test_version_root_and_openapi_schema_are_available(self):
        root = self.client.get(reverse("api_v1:root"))
        self.assertEqual(root.status_code, 200)
        self.assertEqual(root.json(), {"version": "v1", "schema": "/api/v1/schema/"})
        schema = self.client.get(f"{reverse('api_v1:schema')}?format=json")
        self.assertEqual(schema.status_code, 200)
        self.assertIn("openapi", schema.json())
        self.assertIn("/api/v1/auth/token/", schema.json()["paths"])
        self.assertIn("/api/v1/auth/token/refresh/", schema.json()["paths"])
        self.assertIn("/api/v1/donors/", schema.json()["paths"])
        self.assertIn("/api/v1/blood-requests/", schema.json()["paths"])
        self.assertIn("/api/v1/contact-requests/", schema.json()["paths"])

    def test_serializers_have_explicit_private_field_free_allowlists(self):
        self.assertEqual(
            set(DonorSearchSerializer().fields),
            {"id", "public_alias", "blood_group", "availability_status", "division", "district", "upazila", "union", "city_corporation", "city_zone", "ward"},
        )
        self.assertFalse(
            {"user", "phone_e164", "email", "share_phone_after_accept", "share_email_after_accept"}
            & set(DonorSearchSerializer().fields)
        )
        self.assertEqual(
            set(BloodRequestReadSerializer().fields),
            {"id", "blood_group", "units_requested", "required_at", "division", "district", "upazila", "request_location_label", "urgency", "status", "expires_at", "created_at"},
        )
        self.assertFalse({"requester", "facility_name", "facility_address", "description"} & set(BloodRequestReadSerializer().fields))
        self.assertFalse(
            {
                "request_location_latitude",
                "request_location_longitude",
                "request_location_place_id",
                "request_location_source",
                "request_location_confirmed_at",
            }
            & set(BloodRequestReadSerializer().fields)
        )
        self.assertEqual(
            set(ContactRequestReadSerializer().fields),
            {"id", "status", "created_at", "expires_at"},
        )


class ApiTokenAuthenticationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="api-user@example.test",
            password="Synthetic-Unique-Password!947",
            display_name="Synthetic API user",
        )
        self.user.account_status = AccountStatus.ACTIVE
        self.user.save(update_fields=["account_status", "updated_at"])
        self.factory = APIRequestFactory()

    def test_token_issue_rotation_replay_revocation_and_permissions(self):
        response = self.client.post(
            reverse("api_v1:token_obtain"),
            {"identifier": self.user.email, "password": "Synthetic-Unique-Password!947"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        pair = response.json()
        old_access = pair["access_token"]
        old_refresh = pair["refresh_token"]
        self.assertEqual(ApiAccessToken.objects.get().token_digest, digest_token(old_access))
        self.assertEqual(ApiRefreshToken.objects.get().token_digest, digest_token(old_refresh))

        auth = BearerTokenAuthentication()
        request = self.factory.get("/api/v1/protected/", HTTP_AUTHORIZATION=f"Bearer {old_access}")
        authenticated_user, _token = auth.authenticate(request)
        self.assertEqual(authenticated_user, self.user)

        refreshed = self.client.post(
            reverse("api_v1:token_refresh"), {"refresh_token": old_refresh}, format="json"
        )
        self.assertEqual(refreshed.status_code, 200)
        new_pair = refreshed.json()
        self.assertEqual(new_pair["token_type"], "Bearer")
        self.assertEqual(new_pair["expires_in"], 900)
        self.assertIsNotNone(ApiAccessToken.objects.get(token_digest=digest_token(old_access)).revoked_at)

        replay = self.client.post(
            reverse("api_v1:token_refresh"), {"refresh_token": old_refresh}, format="json"
        )
        self.assertEqual(replay.status_code, 401)
        with self.assertRaises(AuthenticationFailed):
            auth.authenticate(self.factory.get(
                "/api/v1/protected/",
                HTTP_AUTHORIZATION=f"Bearer {new_pair['access_token']}",
            ))

    def test_token_credentials_fail_generically_and_refresh_revokes_access(self):
        invalid = self.client.post(
            reverse("api_v1:token_obtain"),
            {"identifier": self.user.email, "password": "wrong password"},
            format="json",
        )
        self.assertEqual(invalid.status_code, 401)
        self.assertEqual(invalid.json()["error"]["code"], "AUTHENTICATION_REQUIRED")
        self.assertEqual(invalid.json()["error"]["request_id"], invalid["X-Request-ID"])

        pair = issue_token_pair(user=self.user)
        revoked = self.client.post(
            reverse("api_v1:token_revoke"), {"refresh_token": pair["refresh_token"]}, format="json"
        )
        self.assertEqual(revoked.status_code, 204)
        with self.assertRaises(AuthenticationFailed):
            BearerTokenAuthentication().authenticate(self.factory.get(
                "/api/v1/protected/",
                HTTP_AUTHORIZATION=f"Bearer {pair['access_token']}",
            ))

    def test_expired_and_suspended_account_access_tokens_are_rejected(self):
        pair = issue_token_pair(user=self.user)
        access = ApiAccessToken.objects.get(token_digest=digest_token(pair["access_token"]))
        access.expires_at = timezone.now()
        access.save(update_fields=["expires_at"])
        request = self.factory.get(
            "/api/v1/protected/", HTTP_AUTHORIZATION=f"Bearer {pair['access_token']}"
        )
        with self.assertRaises(AuthenticationFailed):
            BearerTokenAuthentication().authenticate(request)

        self.user.account_status = AccountStatus.SUSPENDED
        self.user.save(update_fields=["account_status", "updated_at"])
        with self.assertRaises(AuthenticationFailed):
            BearerTokenAuthentication().authenticate(self.factory.get(
                "/api/v1/protected/",
                HTTP_AUTHORIZATION=f"Bearer {pair['access_token']}",
            ))
