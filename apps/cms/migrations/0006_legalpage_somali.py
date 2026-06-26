from django.db import migrations, models


def seed_somali_legal_titles(apps, schema_editor):
    LegalPage = apps.get_model("cms", "LegalPage")
    updates = {
        "privacy": {
            "title_so": "Siyaasadda Asturnaanta",
        },
        "terms": {
            "title_so": "Shuruudaha iyo Xeerarka",
        },
    }
    for page_type, fields in updates.items():
        LegalPage.objects.filter(page_type=page_type).update(**fields)


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0005_legalpage"),
    ]

    operations = [
        migrations.AddField(
            model_name="legalpage",
            name="body_so",
            field=models.TextField(blank=True, help_text="Optional Somali HTML content."),
        ),
        migrations.AddField(
            model_name="legalpage",
            name="title_so",
            field=models.CharField(blank=True, help_text="Somali page title", max_length=200),
        ),
        migrations.RunPython(seed_somali_legal_titles, migrations.RunPython.noop),
    ]
