from django.db import models

from apps.core.models import TimeStampedModel


class LessonProgress(TimeStampedModel):
    student = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="lesson_progress")
    lesson = models.ForeignKey("courses.Lesson", on_delete=models.CASCADE, related_name="progress_records")
    watched_seconds = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    last_watched_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("student", "lesson")
        ordering = ["-last_watched_at"]

    def __str__(self):
        return f"{self.student} - {self.lesson.title}"
