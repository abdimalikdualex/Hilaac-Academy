from django import template

from apps.core.brand_assets import BrandAssetManager

register = template.Library()


@register.inclusion_tag("partials/ha_icon.html")
def ha_icon(name, size=20, class_name="", label=""):
    return {
        "paths": BrandAssetManager.icon_paths(name),
        "size": size,
        "class_name": class_name,
        "label": label,
        "name": name,
    }


@register.inclusion_tag("partials/payment_logo.html")
def payment_logo(method, height=40, class_name=""):
    return {
        "logo_url": BrandAssetManager.payment_logo_url(method),
        "height": height,
        "class_name": class_name,
        "method": method,
    }


def _access_field(access, field, default=""):
    if not access:
        return default
    if isinstance(access, dict):
        return access.get(field, default)
    return getattr(access, field, default)


@register.inclusion_tag("partials/status_badge_icon.html")
def status_badge_icon(access=None, label=None):
    badge_label = label or _access_field(access, "status_label")
    badge = BrandAssetManager.status_badge(badge_label)
    color = _access_field(access, "status_color") or badge.get("color", "slate")
    return {
        "label": badge.get("label", badge_label),
        "icon": badge.get("icon", "circle"),
        "color": color,
    }


@register.inclusion_tag("partials/meta_with_icon.html")
def meta_with_icon(icon, text, class_name=""):
    return {"icon": icon, "text": text, "class_name": class_name}


@register.inclusion_tag("partials/empty_state.html")
def empty_state(name, title, message="", action_url="", action_label=""):
    return {
        "illustration": BrandAssetManager.empty_state(name),
        "title": title,
        "message": message,
        "action_url": action_url,
        "action_label": action_label,
    }


@register.simple_tag
def lesson_type_icon(lesson_type):
    return BrandAssetManager.lesson_icon(lesson_type)


@register.simple_tag
def site_stat_icon(key):
    return BrandAssetManager.site_stat_icon(key)


@register.inclusion_tag("partials/star_rating.html")
def star_rating(rating=5, size=16, class_name="", max_stars=5):
    try:
        stars = int(round(float(rating or 0)))
    except (TypeError, ValueError):
        stars = 0
    stars = max(0, min(stars, max_stars))
    return {
        "rating": stars,
        "size": size,
        "class_name": class_name,
        "max_stars": range(1, max_stars + 1),
    }


@register.inclusion_tag("partials/lesson_type_icon.html")
def render_lesson_icon(lesson):
    return {"icon": lesson.type_icon}
