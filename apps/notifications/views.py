from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from .models import Notification


def _notification_portal_url(user):
    if user.is_super_admin:
        return reverse("admin_portal:notification_list")
    if user.is_instructor:
        return reverse("instructor:notifications")
    return reverse("student:notifications")


@login_required
def notification_list(request):
    return redirect(_notification_portal_url(request.user))


@login_required
def mark_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    if notification.link:
        return redirect(notification.link)
    return redirect(_notification_portal_url(request.user))
