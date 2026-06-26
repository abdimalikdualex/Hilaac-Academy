from django.conf import settings
from django.shortcuts import redirect, render
from django.utils import translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from apps.core.i18n import LANGUAGE_SESSION_KEY, normalize_language, SUPPORTED_UI_LANGUAGES


def page_not_found(request, exception):
    return render(request, "404.html", status=404)


def server_error(request):
    return render(request, "500.html", status=500)


@csrf_protect
@require_POST
def set_language(request):
    lang = normalize_language(request.POST.get("language"))
    if lang not in SUPPORTED_UI_LANGUAGES:
        lang = "en"

    request.session[LANGUAGE_SESSION_KEY] = lang
    request.session.modified = True
    try:
        request.session.save()
    except AttributeError:
        pass

    if request.user.is_authenticated:
        request.user.language_preference = lang
        request.user.save(update_fields=["language_preference"])

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"
    if not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = "/"

    translation.activate(lang)
    request.LANGUAGE_CODE = lang
    response = redirect(next_url)
    response.set_cookie(
        settings.LANGUAGE_COOKIE_NAME,
        lang,
        max_age=365 * 24 * 60 * 60,
        path="/",
        samesite=settings.SESSION_COOKIE_SAMESITE,
        secure=settings.SESSION_COOKIE_SECURE if hasattr(settings, "SESSION_COOKIE_SECURE") else False,
    )
    return response
