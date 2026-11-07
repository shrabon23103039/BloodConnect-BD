"""Small cache-backed fixed-window throttles for sensitive account forms."""

from functools import wraps
import hmac
from hashlib import sha256

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse


def limited_by_ip(*, scope: str, limit: int, window_seconds: int, methods=None, api_response=False):
    """Rate-limit requests by remote address without storing the address itself."""

    def decorate(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            request = args[0] if hasattr(args[0], "META") else args[1]
            if methods is None or request.method.upper() in methods:
                remote_address = request.META.get("REMOTE_ADDR", "unknown")
                digest = hmac.new(
                    settings.SECRET_KEY.encode("utf-8"),
                    remote_address.encode("utf-8"),
                    sha256,
                ).hexdigest()
                cache_key = f"accounts:throttle:{scope}:{digest}"
                if not cache.add(cache_key, 1, timeout=window_seconds):
                    try:
                        count = cache.incr(cache_key)
                    except ValueError:
                        cache.add(cache_key, 1, timeout=window_seconds)
                        count = 1
                    if count > limit:
                        if api_response:
                            request_id = getattr(
                                getattr(request, "_request", request),
                                "request_id",
                                "",
                            )
                            response = JsonResponse(
                                {
                                    "error": {
                                        "code": "RATE_LIMITED",
                                        "message": "Too many requests. Please wait before trying again.",
                                        "request_id": request_id,
                                    }
                                },
                                status=429,
                            )
                            response["Retry-After"] = str(window_seconds)
                            return response
                        response = HttpResponse(
                            "Too many attempts. Please wait before trying again.",
                            status=429,
                            content_type="text/plain; charset=utf-8",
                        )
                        response["Retry-After"] = str(window_seconds)
                        return response
            return view_func(*args, **kwargs)

        return wrapped

    return decorate
