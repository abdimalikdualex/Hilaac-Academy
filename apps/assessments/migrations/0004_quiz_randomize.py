from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assessments", "0003_assessment_mvp_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="quiz",
            name="randomize_questions",
            field=models.BooleanField(default=False, help_text="Shuffle question order for each attempt."),
        ),
        migrations.AddField(
            model_name="quiz",
            name="questions_per_attempt",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="If set, only this many random questions are shown per attempt.",
                null=True,
            ),
        ),
    ]
