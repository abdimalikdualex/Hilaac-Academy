from django.db import models

from apps.core.models import TimeStampedModel


class Notification(TimeStampedModel):
    class NotificationType(models.TextChoices):
        ENROLLMENT = "enrollment", "Enrollment"
        PAYMENT = "payment", "Payment"
        QUIZ = "quiz", "Quiz"
        CERTIFICATE = "certificate", "Certificate"
        ASSIGNMENT = "assignment", "Assignment"
        SYSTEM = "system", "System"
        GENERAL = "general", "General"

    class Severity(models.TextChoices):
        INFO = "info", "Information"
        SUCCESS = "success", "Success"
        WARNING = "warning", "Warning"
        IMPORTANT = "important", "Important Announcement"

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices, default=NotificationType.GENERAL)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.INFO)
    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=500, blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_notifications",
    )
    is_system = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.message[:50]}"
