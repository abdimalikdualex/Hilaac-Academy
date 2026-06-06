from django.db import migrations, models


def mark_demo_seeded_if_courses_exist(apps, schema_editor):
    SiteSettings = apps.get_model("core", "SiteSettings")
    Level = apps.get_model("courses", "Level")
    site, _ = SiteSettings.objects.get_or_create(pk=1)
    if Level.objects.exists():
        site.demo_content_seeded = True
        site.save(update_fields=["demo_content_seeded"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_sitesettings"),
        ("courses", "0011_level_soft_delete"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="demo_content_seeded",
            field=models.BooleanField(
                default=False,
                help_text="Set after first demo seed so deploys never restore deleted demo courses.",
            ),
        ),
        migrations.RunPython(mark_demo_seeded_if_courses_exist, migrations.RunPython.noop),
    ]
