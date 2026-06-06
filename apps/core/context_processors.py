from django.conf import settings

from apps.payments.currency import detect_country_code, get_display_currency


def site_settings(request):
    from apps.core.branding import resolve_hero_background_url, resolve_hero_srcset, resolve_site_branding
    from apps.core.roles import role_dashboard_name

    dashboard_url_name = ""
    if request.user.is_authenticated:
        dashboard_url_name = role_dashboard_name(request.user)

    from apps.core.brand_assets import BrandAssetManager

    return {
        **resolve_site_branding(),
        "brand": BrandAssetManager,
        "SITE_URL": settings.SITE_URL,
        "WHATSAPP_SUPPORT_NUMBER": settings.WHATSAPP_SUPPORT_NUMBER,
        "WHATSAPP_LINK": f"https://wa.me/{settings.WHATSAPP_SUPPORT_NUMBER.replace('+', '')}",
        "DASHBOARD_URL_NAME": dashboard_url_name,
        "hero_background_url": resolve_hero_background_url(),
        "hero_srcset": resolve_hero_srcset(),
        "REQUIRE_EMAIL_VERIFICATION": settings.REQUIRE_EMAIL_VERIFICATION,
        "user_country_code": detect_country_code(request, getattr(request, "user", None)),
        "user_display_currency": get_display_currency(detect_country_code(request, getattr(request, "user", None))),
    }
