from django.urls import reverse

from .models import Notification


def _notifications_url(user):
    if not user.is_authenticated:
        return reverse("notifications:list")
    if user.is_super_admin:
        return reverse("admin_portal:my_notifications")
    if user.is_instructor:
        return reverse("instructor:notifications")
    return reverse("student:notifications")


def unread_notifications(request):
    if request.user.is_authenticated:
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return {
            "unread_notification_count": count,
            "notifications_url": _notifications_url(request.user),
        }
    return {"unread_notification_count": 0, "notifications_url": reverse("notifications:list")}