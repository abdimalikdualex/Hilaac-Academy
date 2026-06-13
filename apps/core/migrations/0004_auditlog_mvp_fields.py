from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_sitesettings_demo_content_seeded"),
    ]

    operations = [
        migrations.AddField(
            model_name="auditlog",
            name="user_display_name",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="auditlog",
            name="user_role",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="auditlog",
            name="module",
            field=models.CharField(blank=True, db_index=True, max_length=50),
        ),
        migrations.AddField(
            model_name="auditlog",
            name="description",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="auditlog",
            name="old_values",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="auditlog",
            name="new_values",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="auditlog",
            name="user_agent",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="auditlog",
            name="status",
            field=models.CharField(
                choices=[("success", "Success"), ("failed", "Failed")],
                db_index=True,
                default="success",
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="auditlog",
            name="action",
            field=models.CharField(db_index=True, max_length=100),
        ),
        migrations.AlterField(
            model_name="auditlog",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["-created_at", "module"], name="core_auditl_created_module_idx"),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["user_role", "-created_at"], name="core_auditl_user_role_created_idx"),
        ),
    ]
