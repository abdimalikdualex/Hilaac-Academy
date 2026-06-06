from django.db import migrations


def promote_superusers(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(is_superuser=True).exclude(role="super_admin").update(
        role="super_admin",
        is_verified=True,
        is_staff=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_user_bio_alter_user_role"),
    ]

    operations = [
        migrations.RunPython(promote_superusers, migrations.RunPython.noop),
    ]
