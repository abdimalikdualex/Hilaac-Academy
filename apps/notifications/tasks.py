from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail


def dispatch_email_task(subject, message, recipient_email, html_message=None):
    """Send immediately in dev or when Celery is unavailable; queue otherwise."""
    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        send_email_task(subject, message, recipient_email, html_message)
        return
    try:
        send_email_task.delay(subject, message, recipient_email, html_message)
    except Exception:
        send_email_task(subject, message, recipient_email, html_message)


@shared_task
def send_email_task(subject, message, recipient_email, html_message=None):
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient_email],
        fail_silently=False,
        html_message=html_message,
    )


@shared_task
def send_quiz_reminders():
    """Send reminders for students with incomplete courses (weekly Celery beat task)."""
    from apps.courses.models import Enrollment
    from apps.notifications.services import notify_quiz_reminder

    for enrollment in Enrollment.objects.filter(status=Enrollment.Status.ACTIVE).select_related("student", "level"):
        if enrollment.progress_percentage < 100:
            notify_quiz_reminder(enrollment.student, enrollment.level, enrollment.progress_percentage)
