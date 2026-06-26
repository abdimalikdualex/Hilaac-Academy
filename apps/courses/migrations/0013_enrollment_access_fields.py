from django.db import migrations, models


def grant_existing_enrollments(apps, schema_editor):
    Enrollment = apps.get_model("courses", "Enrollment")
    Enrollment.objects.exclude(status="cancelled").update(
        access_granted=True,
        payment_verified=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0012_default_languages"),
    ]

    operations = [
        migrations.AddField(
            model_name="enrollment",
            name="access_granted",
            field=models.BooleanField(
                default=False,
                help_text="Student can access course materials (set after payment approval or free enrollment).",
            ),
        ),
        migrations.AddField(
            model_name="enrollment",
            name="payment_verified",
            field=models.BooleanField(
                default=False,
                help_text="Paid enrollment confirmed by admin after successful payment.",
            ),
        ),
        migrations.RunPython(grant_existing_enrollments, migrations.RunPython.noop),
    ]
