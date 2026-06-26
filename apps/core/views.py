from django.shortcuts import redirect, render
from django.utils import translation
from django.views.decorators.http import require_POST

from apps.core.i18n import normalize_language, SUPPORTED_UI_LANGUAGES


def page_not_found(request, exception):
    return render(request, "404.html", status=404)


def server_error(request):
    return render(request, "500.html", status=500)


@require_POST
def set_language(request):
    lang = normalize_language(request.POST.get("language"))
    if lang not in SUPPORTED_UI_LANGUAGES:
        lang = "en"
    request.session[translation.LANGUAGE_SESSION_KEY] = lang
    if request.user.is_authenticated:
        request.user.language_preference = lang
        request.user.save(update_fields=["language_preference"])
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"
    return redirect(next_url)
