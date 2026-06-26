from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import translation

class UserLocaleMiddleware:
    """Activate English or Somali from user preference, session, or browser."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from apps.core.i18n import LANGUAGE_SESSION_KEY, resolve_request_language

        lang = resolve_request_language(request)
        if request.session.get(LANGUAGE_SESSION_KEY) != lang:
            request.session[LANGUAGE_SESSION_KEY] = lang
        translation.activate(lang)
        request.LANGUAGE_CODE = lang
        return self.get_response(request)


class EmailVerificationMiddleware:
    """
    Email verification is required only for sensitive actions — not for purchasing courses.
    Unverified students may browse, wishlist, checkout, pay, and learn after approval.
    """

    VERIFICATION_REQUIRED_PREFIXES = (
        "/student/certificates/",
        "/student/settings/password/",
        "/certificates/download/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not settings.REQUIRE_EMAIL_VERIFICATION:
            return self.get_response(request)
        if request.user.is_authenticated and request.user.is_student and not request.user.is_verified:
            path = request.path
            if any(path.startswith(p) for p in self.VERIFICATION_REQUIRED_PREFIXES):
                messages.warning(
                    request,
                    "Please verify your email to access this feature.",
                )
                return redirect("accounts:verify_notice")
        return self.get_response(request)


class RoleAccessMiddleware:
    """Block cross-role URL access before views run. Returns 403 for wrong role."""

    # prefix -> allowed role names (see apps.core.permissions._user_has_role)
    ROLE_PREFIXES = (
        ("/admin-portal/", ("super_admin",)),
        ("/instructor/", ("instructor",)),
        ("/student/", ("student",)),
        ("/dashboard/", ("student",)),
        ("/payments/", ("student",)),
        ("/certificates/my", ("student",)),
        ("/certificates/download/", ("student",)),
    )

    PUBLIC_PREFIXES = (
        "/static/",
        "/media/",
        "/i18n/",
        "/accounts/login",
        "/accounts/register",
        "/accounts/password/",
        "/accounts/verify",
        "/courses/",
        "/certificates/verify/",
        "/payments/mpesa/callback",
    )

    LOGIN_REQUIRED_PREFIXES = (
        "/student/",
        "/dashboard/",
        "/payments/",
        "/certificates/my",
        "/certificates/download/",
        "/quizzes/",
        "/notifications/",
        "/library/",
        "/accounts/dashboard",
        "/accounts/profile",
        "/admin-portal/",
        "/instructor/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        if any(path.startswith(p) for p in self.PUBLIC_PREFIXES):
            return self.get_response(request)

        if path == "/" or path.startswith("/accounts/") and not path.startswith("/accounts/dashboard") and not path.startswith("/accounts/profile"):
            return self.get_response(request)

        user = request.user

        if not user.is_authenticated:
            if any(path.startswith(p) for p in self.LOGIN_REQUIRED_PREFIXES):
                login_url = reverse("accounts:login")
                if path != login_url:
                    return redirect(f"{login_url}?next={path}")
            return self.get_response(request)

        from django.core.exceptions import PermissionDenied

        from apps.core.permissions import _user_has_role

        for prefix, roles in self.ROLE_PREFIXES:
            if path.startswith(prefix):
                if not any(_user_has_role(user, r) for r in roles):
                    raise PermissionDenied("You do not have permission to access this area.")
                break

        return self.get_response(request)
