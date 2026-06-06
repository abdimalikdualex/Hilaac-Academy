from django import template

from apps.core.imaging import responsive_image_data, responsive_static_image_data, static_url

register = template.Library()


@register.inclusion_tag("partials/responsive_image.html")
def responsive_image(image_field, preset="course_cover", alt="", css_class="", loading="lazy", fetchpriority=""):
    data = responsive_image_data(
        image_field,
        preset=preset,
        placeholder=static_url("images/course-placeholder.svg"),
    )
    return {
        "src": data["src"],
        "srcset": data["srcset"],
        "sizes": data["sizes"],
        "alt": alt,
        "css_class": css_class,
        "loading": loading,
        "fetchpriority": fetchpriority,
        "is_placeholder": data.get("is_placeholder", False),
    }


@register.inclusion_tag("partials/responsive_image.html")
def static_responsive_image(stem, preset="feature_card", alt="", css_class="", loading="lazy", fetchpriority=""):
    data = responsive_static_image_data(stem, preset=preset)
    return {
        "src": data["src"],
        "srcset": data["srcset"],
        "sizes": data["sizes"],
        "alt": alt,
        "css_class": css_class,
        "loading": loading,
        "fetchpriority": fetchpriority,
        "is_placeholder": False,
    }


@register.inclusion_tag("partials/skeleton_card.html")
def skeleton_cards(count=6):
    return {"count": range(count)}
