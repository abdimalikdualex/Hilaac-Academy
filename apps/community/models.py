from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class DiscussionThread(TimeStampedModel):
    level = models.ForeignKey("courses.Level", on_delete=models.CASCADE, related_name="discussion_threads")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="discussion_threads",
    )
    title = models.CharField(max_length=200)
    body = models.TextField()
    is_pinned = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_pinned", "-created_at"]

    def __str__(self):
        return self.title

    @property
    def reply_count(self):
        return self.replies.count()


class DiscussionReply(TimeStampedModel):
    thread = models.ForeignKey(DiscussionThread, on_delete=models.CASCADE, related_name="replies")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="discussion_replies",
    )
    body = models.TextField()
    is_instructor_reply = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Reply by {self.author} on {self.thread_id}"


class LiveClassSession(TimeStampedModel):
    class Platform(models.TextChoices):
        ZOOM = "zoom", "Zoom"
        MEET = "meet", "Google Meet"
        HILAAC = "hilaac", "Hilaac Live"
        OTHER = "other", "Other"

    level = models.ForeignKey("courses.Level", on_delete=models.CASCADE, related_name="live_sessions")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    meeting_url = models.URLField(help_text="Zoom, Google Meet, or live session link")
    platform = models.CharField(max_length=20, choices=Platform.choices, default=Platform.ZOOM)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="live_sessions_created",
    )
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["starts_at"]

    def __str__(self):
        return f"{self.title} ({self.starts_at:%Y-%m-%d %H:%M})"

    @property
    def ends_at(self):
        return self.starts_at + timezone.timedelta(minutes=self.duration_minutes)

    @property
    def is_upcoming(self):
        return self.ends_at >= timezone.now()

    @property
    def is_live_now(self):
        now = timezone.now()
        return self.starts_at <= now <= self.ends_at
