"""Dependency-aware liveness and readiness endpoints."""

import os

import redis
from django.db import DatabaseError, connections
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


def _database_status() -> str:
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except (DatabaseError, OSError):
        return "unavailable"
    return "ok"


def _redis_status() -> str:
    redis_url = os.environ.get("REDIS_URL", "")
    if not redis_url:
        return "not_configured"

    client = None
    try:
        client = redis.Redis.from_url(
            redis_url,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        client.ping()
    except (redis.RedisError, OSError, ValueError):
        return "unavailable"
    finally:
        if client is not None:
            try:
                client.close()
            except (redis.RedisError, OSError):
                pass
    return "ok"


@never_cache
@require_GET
def liveness(request):
    """Report only that the process can serve a request."""
    return JsonResponse({"status": "alive"})


@never_cache
@require_GET
def readiness(request):
    """Report each required dependency without exposing its configuration."""
    dependencies = {
        "database": _database_status(),
        "redis": _redis_status(),
    }
    ready = all(status == "ok" for status in dependencies.values())
    return JsonResponse(
        {
            "status": "ready" if ready else "not_ready",
            "dependencies": dependencies,
        },
        status=200 if ready else 503,
    )
