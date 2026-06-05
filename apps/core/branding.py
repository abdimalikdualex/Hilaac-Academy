"""Resolve branded static assets for templates."""
from django.contrib.staticfiles import finders
from django.templatetags.static import static

HERO_BACKGROUND_CANDIDATES = (
    "images/hero-4k.webp",
    "images/hero.webp",
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
    """Responsive hero sources: mobile/tablet/desktop (4K on large screens)."""
    sources = {
        "default": resolve_hero_background_url(),
        "tablet": static("images/hero-tablet.webp") if finders.find("images/hero-tablet.webp") else None,
        "desktop_4k": static("images/hero-4k.webp") if finders.find("images/hero-4k.webp") else None,
        "fallback": static("images/hero.webp") if finders.find("images/hero.webp") else resolve_hero_background_url(),
    }
    if not sources["tablet"]:
        sources["tablet"] = sources["fallback"]
    if not sources["desktop_4k"]:
        sources["desktop_4k"] = sources["fallback"]
    return sources
