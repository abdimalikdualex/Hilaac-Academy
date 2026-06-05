from functools import wraps

from django.core.cache import cache
from django.http import HttpRequest, HttpResponseForbidden

from .models import AuditLog


def get_client_ip(request):
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_audit(request, action, model_name="", object_id="", details=""):
    AuditLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        action=action,
        model_name=model_name,
        object_id=str(object_id),
        details=details,
        ip_address=get_client_ip(request),
    )


def _extract_request(args):
    """Get HttpRequest from view args (works for FBV and CBV methods)."""
    for arg in args:
        if isinstance(arg, HttpRequest):
            return arg
    return None


def rate_limit(key_prefix, limit=5, period=300):
    """Simple cache-based rate limiter (limit requests per period seconds)."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            request = _extract_request(args)
            if request is None:
                return view_func(*args, **kwargs)

            ip = get_client_ip(request) or "unknown"
            cache_key = f"ratelimit:{key_prefix}:{ip}"
            count = cache.get(cache_key, 0)
            if count >= limit:
                return HttpResponseForbidden("Too many requests. Please try again later.")
            cache.set(cache_key, count + 1, period)
            return view_func(*args, **kwargs)

        return wrapper

    return decorator
