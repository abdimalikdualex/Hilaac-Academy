from django.db import migrations, models


def publish_existing_assessments(apps, schema_editor):
    Assignment = apps.get_model("assessments", "Assignment")
    Quiz = apps.get_model("assessments", "Quiz")
    Assignment.objects.all().update(is_published=True)
    Quiz.objects.all().update(is_published=True)


class Migration(migrations.Migration):
    dependencies = [
        ("assessments", "0002_assignment_assignmentsubmission"),
    ]

    operations = [
        migrations.AddField(
            model_name="assignment",
            name="allow_resubmit",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="assignment",
            name="attachment",
            field=models.FileField(blank=True, null=True, upload_to="assignments/attachments/"),
        ),
        migrations.AddField(
            model_name="assignment",
            name="instructions",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="assignment",
            name="is_published",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="assignmentsubmission",
            name="graded_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="assignmentsubmission",
            name="notes",
            field=models.TextField(blank=True, help_text="Student submission notes"),
        ),
        migrations.AlterField(
            model_name="assignmentsubmission",
            name="grade",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Marks obtained",
                max_digits=7,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="assignmentsubmission",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("submitted", "Submitted"),
                    ("under_review", "Under Review"),
                    ("graded", "Graded"),
                    ("late", "Late Submission"),
                    ("resubmit", "Return for Correction"),
                    ("approved", "Approved"),
                ],
                default="submitted",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="quiz",
            name="description",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="quiz",
            name="is_published",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="quiz",
            name="max_attempts",
            field=models.PositiveIntegerField(default=3, help_text="Maximum attempts per student"),
        ),
        migrations.AddField(
            model_name="quiz",
            name="show_correct_answers",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="question",
            name="question_type",
            field=models.CharField(
                choices=[
                    ("mcq", "Multiple Choice"),
                    ("true_false", "True/False"),
                    ("multi_answer", "Multiple Answers"),
                    ("fill_blank", "Short Answer"),
                    ("reading", "Reading Comprehension"),
                    ("listening", "Listening"),
                ],
                default="mcq",
                max_length=20,
            ),
        ),
        migrations.RunPython(publish_existing_assessments, migrations.RunPython.noop),
    ]
