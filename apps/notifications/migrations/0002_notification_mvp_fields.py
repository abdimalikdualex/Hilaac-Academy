from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="sent_notifications",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="notification",
            name="is_system",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="notification",
            name="severity",
            field=models.CharField(
                choices=[
                    ("info", "Information"),
                    ("success", "Success"),
                    ("warning", "Warning"),
                    ("important", "Important Announcement"),
                ],
                default="info",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="notification",
            name="title",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name="notification",
            name="notification_type",
            field=models.CharField(
                choices=[
                    ("enrollment", "Enrollment"),
                    ("payment", "Payment"),
                    ("quiz", "Quiz"),
                    ("certificate", "Certificate"),
                    ("assignment", "Assignment"),
                    ("system", "System"),
                    ("general", "General"),
                ],
                default="general",
                max_length=20,
            ),
        ),
    ]
