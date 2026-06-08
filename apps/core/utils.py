import logging
from functools import wraps

from django.core.cache import cache
from django.http import HttpRequest, HttpResponseForbidden

from .models import AuditLog

audit_logger = logging.getLogger("hilaac.audit")
security_logger = logging.getLogger("django.security")


def get_client_ip(request):
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_audit(request, action, model_name="", object_id="", details=""):
    ip = get_client_ip(request)
    user = request.user if request.user.is_authenticated else None
    AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=str(object_id),
        details=details,
        ip_address=ip,
    )
    audit_logger.info(
        "action=%s user=%s model=%s object=%s ip=%s details=%s",
        action,
        getattr(user, "username", "anonymous"),
        model_name,
        object_id,
        ip,
        details,
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
                security_logger.warning(
                    "rate_limit_block prefix=%s ip=%s path=%s", key_prefix, ip, request.path
                )
                return HttpResponseForbidden("Too many requests. Please try again later.")
            cache.set(cache_key, count + 1, period)
            return view_func(*args, **kwargs)

        return wrapper

    return decorator
