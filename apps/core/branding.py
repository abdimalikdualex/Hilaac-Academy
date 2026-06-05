"""Resolve branded static assets for templates."""
from django.contrib.staticfiles import finders
from django.templatetags.static import static

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
