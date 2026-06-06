"""Platform-wide cache versioning — bump once to invalidate all derived caches."""
from django.core.cache import cache

CACHE_VERSION_KEY = "platform:cache_version"
HOME_CONTEXT_PREFIX = "cms:home:context"
COURSE_DETAIL_PREFIX = "course:detail"


def get_cache_version():
    return cache.get(CACHE_VERSION_KEY, 1)


def bump_cache_version():
    try:
        cache.incr(CACHE_VERSION_KEY)
    except ValueError:
        cache.set(CACHE_VERSION_KEY, 2, None)


def home_cache_key():
    return f"{HOME_CONTEXT_PREFIX}:v{get_cache_version()}"


def course_detail_cache_key(language_slug, level_slug):
    return f"{COURSE_DETAIL_PREFIX}:{language_slug}:{level_slug}:v{get_cache_version()}"


def invalidate_platform_cache():
    """Invalidate all versioned platform caches after any admin/content change."""
    bump_cache_version()
