"""Resolve branded static assets for templates."""
from django.contrib.staticfiles import finders
from django.templatetags.static import static

from apps.core.models import SiteSettings


def resolve_site_branding():
    """Single source of truth for academy name, logo, and contact info."""
    site = SiteSettings.get()
    logo_url = site.logo.url if site.logo else static("images/logo-nav.webp")
    return {
        "site": site,
        "SITE_NAME": site.academy_name or "Hilaac Academy",
        "SITE_TAGLINE": site.tagline or "Baro Xirfado Casri ah, Dhis Mustaqbalkaaga",
        "site_logo_url": logo_url,
        "site_banner_url": site.banner.url if site.banner else None,
        "site_footer_text": site.footer_text,
        "site_contact_email": site.contact_email,
        "site_contact_phone": site.contact_phone or site.whatsapp_number,
        "site_whatsapp_number": site.whatsapp_number,
    }

HERO_BACKGROUND_CANDIDATES = (
    "images/hero-full.webp",
    "images/hero.webp",
    "images/hero-tablet.webp",
    "images/hero.png",
    "images/hero.jpg",
    "images/hero.jpeg",
    "images/hero-education.svg",
)


def resolve_hero_background_url():
    """Return the best available hero background for general use."""
    for path in HERO_BACKGROUND_CANDIDATES:
        if finders.find(path):
            return static(path)
    return static("images/hero-education.svg")


def resolve_hero_srcset():
    """Responsive hero sources capped at 1920x1080 — no 4K delivery."""
    fallback = static("images/hero.webp") if finders.find("images/hero.webp") else resolve_hero_background_url()
    tablet = static("images/hero-tablet.webp") if finders.find("images/hero-tablet.webp") else fallback
    desktop = static("images/hero-full.webp") if finders.find("images/hero-full.webp") else fallback
    if finders.find("images/hero-4k.webp") and not finders.find("images/hero-full.webp"):
        desktop = static("images/hero-4k.webp")
    return {
        "default": resolve_hero_background_url(),
        "tablet": tablet,
        "desktop": desktop,
        "desktop_4k": desktop,
        "fallback": fallback,
    }
