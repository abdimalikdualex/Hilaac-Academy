from django.db import models

from apps.core.models import TimeStampedModel
from apps.core.soft_delete import SoftDeleteMixin


class LibraryResource(SoftDeleteMixin, TimeStampedModel):
    class Category(models.TextChoices):
        ENGLISH_NOTES = "english_notes", "English Notes"
        KISWAHILI_NOTES = "kiswahili_notes", "Kiswahili Notes"
        VOCABULARY = "vocabulary", "Vocabulary Books"
        GRAMMAR = "grammar", "Grammar Guides"
        WORKSHEETS = "worksheets", "Worksheets"

    title = models.CharField(max_length=200)
    category = models.CharField(max_length=30, choices=Category.choices)
    language = models.ForeignKey("courses.Language", on_delete=models.CASCADE, related_name="library_resources")
    description = models.TextField(blank=True)
    file = models.FileField(upload_to="library/")
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "title"]

    def __str__(self):
        return self.title
