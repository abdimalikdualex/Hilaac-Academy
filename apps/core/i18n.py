"""UI language helpers for English + Af-Soomaali."""
from contextlib import contextmanager
from typing import Optional

from django.conf import settings
from django.utils import translation

SUPPORTED_UI_LANGUAGES = ("en", "so")
# Django 4.2+ removed translation.LANGUAGE_SESSION_KEY; cookie name is the standard key.
LANGUAGE_SESSION_KEY = settings.LANGUAGE_COOKIE_NAME

def normalize_language(code: Optional[str]) -> str:
    if not code:
        return "en"
    code = str(code).strip().lower()[:5]
    if code.startswith("so"):
        return "so"
    return "en"


def resolve_request_language(request) -> str:
    """Session/cookie (explicit user choice) beat profile default."""
    session_lang = request.session.get(LANGUAGE_SESSION_KEY)
    if session_lang in SUPPORTED_UI_LANGUAGES:
        return session_lang
    cookie_lang = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
    if cookie_lang in SUPPORTED_UI_LANGUAGES:
        return cookie_lang
    if getattr(request, "user", None) and request.user.is_authenticated:
        pref = getattr(request.user, "language_preference", None)
        if pref in SUPPORTED_UI_LANGUAGES:
            return pref
    accept = request.META.get("HTTP_ACCEPT_LANGUAGE", "").lower()
    if "so" in accept:
        return "so"
    return "en"


@contextmanager
def user_language(user):
    lang = "en"
    if user and getattr(user, "is_authenticated", False):
        lang = normalize_language(getattr(user, "language_preference", "en"))
    translation.activate(lang)
    try:
        yield lang
    finally:
        translation.deactivate()


def activate_language(lang: str):
    translation.activate(normalize_language(lang))
