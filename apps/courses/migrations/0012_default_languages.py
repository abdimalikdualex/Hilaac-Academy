from django.db import migrations


def seed_default_languages(apps, schema_editor):
    Language = apps.get_model("courses", "Language")
    defaults = (
        ("english", "English", "Learn English from beginner to expert level."),
        ("kiswahili", "Kiswahili", "Learn Kiswahili from beginner to advanced level."),
    )
    for slug, name, description in defaults:
        Language.objects.get_or_create(
            slug=slug,
            defaults={"name": name, "description": description, "is_active": True},
        )


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0011_level_soft_delete"),
    ]

    operations = [
        migrations.RunPython(seed_default_languages, migrations.RunPython.noop),
    ]
