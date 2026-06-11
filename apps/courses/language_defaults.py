"""Default course categories (languages) used across forms and catalog filters."""

DEFAULT_LANGUAGES = (
    {
        "slug": "english",
        "name": "English",
        "description": "Learn English from beginner to expert level.",
    },
    {
        "slug": "kiswahili",
        "name": "Kiswahili",
        "description": "Learn Kiswahili from beginner to advanced level.",
    },
)


def ensure_default_languages():
    """Create English and Kiswahili categories if the database has none yet."""
    from .models import Language

    for item in DEFAULT_LANGUAGES:
        Language.objects.get_or_create(
            slug=item["slug"],
            defaults={
                "name": item["name"],
                "description": item["description"],
                "is_active": True,
            },
        )


def active_language_queryset():
    from .models import Language

    ensure_default_languages()
    return Language.objects.filter(is_active=True).order_by("name")
