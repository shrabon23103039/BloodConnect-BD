import json
import logging
from unittest.mock import MagicMock, patch

import redis
from django.db import DatabaseError
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse

from config.health import _database_status, _redis_status
from config.logging import JsonFormatter
from config.middleware import RequestLoggingMiddleware


class HealthEndpointTests(TestCase):
    def test_liveness_does_not_depend_on_services(self):
        with patch("config.health._database_status", side_effect=AssertionError):
            response = self.client.get(reverse("health_live"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "alive"})
        self.assertEqual(response["Cache-Control"], "max-age=0, no-cache, no-store, must-revalidate, private")

    def test_readiness_distinguishes_database_and_redis_failures(self):
        with (
            patch("config.health._database_status", return_value="unavailable"),
            patch("config.health._redis_status", return_value="not_configured"),
        ):
            response = self.client.get(reverse("health_ready"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {
                "status": "not_ready",
                "dependencies": {
                    "database": "unavailable",
                    "redis": "not_configured",
                },
            },
        )

    def test_readiness_is_ready_only_when_both_dependencies_are_healthy(self):
        with (
            patch("config.health._database_status", return_value="ok"),
            patch("config.health._redis_status", return_value="ok"),
        ):
            response = self.client.get(reverse("health_ready"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ready", "dependencies": {"database": "ok", "redis": "ok"}},
        )

    def test_database_check_runs_a_minimal_query_and_redacts_errors(self):
        fake_connection = MagicMock()
        fake_cursor = fake_connection.cursor.return_value.__enter__.return_value
        fake_cursor.execute.side_effect = DatabaseError("password=private-database-secret")

        with patch("config.health.connections") as connection_handler:
            connection_handler.__getitem__.return_value = fake_connection
            result = _database_status()

        self.assertEqual(result, "unavailable")

    def test_redis_check_reports_missing_or_failed_service_without_details(self):
        with patch.dict("os.environ", {"REDIS_URL": ""}):
            self.assertEqual(_redis_status(), "not_configured")

        fake_client = MagicMock()
        fake_client.ping.side_effect = redis.RedisError("password=private-redis-secret")
        with (
            patch.dict("os.environ", {"REDIS_URL": "redis://private-redis-secret@cache:6379/0"}),
            patch("config.health.redis.Redis.from_url", return_value=fake_client) as from_url,
        ):
            result = _redis_status()

        self.assertEqual(result, "unavailable")
        self.assertEqual(from_url.call_args.kwargs["socket_timeout"], 1)
        fake_client.close.assert_called_once_with()

    def test_health_response_never_exposes_dependency_configuration(self):
        with (
            patch("config.health._database_status", return_value="unavailable"),
            patch("config.health._redis_status", return_value="unavailable"),
        ):
            response = self.client.get(reverse("health_ready"))

        self.assertNotContains(response, "postgresql://", status_code=503)
        self.assertNotContains(response, "redis://", status_code=503)
        self.assertNotContains(response, "private-secret", status_code=503)


class RequestLoggingTests(TestCase):
    def test_log_contains_only_allowlisted_request_metadata(self):
        request = RequestFactory().get(
            "/health/ready/?phone=01700000000&token=private-token",
            HTTP_X_REQUEST_ID="attacker-controlled-request-id",
        )
        middleware = RequestLoggingMiddleware(lambda _request: HttpResponse("ok"))

        with self.assertLogs("bloodconnect.request", level="INFO") as captured:
            response = middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertRegex(response["X-Request-ID"], r"^[0-9a-f]{32}$")
        self.assertNotEqual(response["X-Request-ID"], "attacker-controlled-request-id")
        record = captured.records[0]
        serialized = JsonFormatter().format(record)
        payload = json.loads(serialized)
        self.assertEqual(payload["request_id"], response["X-Request-ID"])
        self.assertEqual(payload["status_code"], 200)
        for secret in ("01700000000", "private-token", "attacker-controlled-request-id"):
            self.assertNotIn(secret, serialized)

    def test_formatter_omits_messages_and_arbitrary_personal_fields(self):
        record = logging.LogRecord(
            "bloodconnect.request",
            logging.INFO,
            __file__,
            1,
            "password=private-password phone=01700000000",
            (),
            None,
        )
        record.event = "request_completed"
        record.method = "GET"
        record.status_code = 200
        record.duration_ms = 1.0
        record.request_id = "safe-correlation-id"
        record.phone = "01700000000"

        serialized = JsonFormatter().format(record)

        self.assertNotIn("private-password", serialized)
        self.assertNotIn("01700000000", serialized)
        self.assertEqual(json.loads(serialized)["event"], "request_completed")

    def test_non_get_health_requests_are_rejected(self):
        response = self.client.post(reverse("health_live"))
        self.assertEqual(response.status_code, 405)
