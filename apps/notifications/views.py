from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.core.pagination import NOTIFICATION_PAGE_SIZE, paginate_queryset

from .models import Notification


def _notification_portal_url(user):
    if user.is_super_admin:
        return reverse("admin_portal:notification_list")
    if user.is_instructor:
        return reverse("instructor:notifications")
    return reverse("student:notifications")


@login_required
def notification_list(request):
    notes = Notification.objects.filter(user=request.user).order_by("-created_at")
    page = paginate_queryset(request, notes, per_page=NOTIFICATION_PAGE_SIZE)
    return redirect(_notification_portal_url(request.user))


@login_required
def mark_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    if request.method == "GET" and notification.link:
        return redirect(notification.link)
    return redirect(_notification_portal_url(request.user))


@login_required
@require_POST
def mark_read_api(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return JsonResponse({"ok": True})


@login_required
@require_POST
def delete_notification(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.delete()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"ok": True})
    return redirect(_notification_portal_url(request.user))


@login_required
def recent_dropdown(request):
    notes = list(
        Notification.objects.filter(user=request.user).order_by("-created_at")[:8]
    )
    unread = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse(
        {
            "unread_count": unread,
            "notifications": [
                {
                    "id": n.pk,
                    "title": n.title or n.message[:60],
                    "message": n.message[:120],
                    "is_read": n.is_read,
                    "link": n.link,
                    "severity": n.severity,
                    "created_at": n.created_at.strftime("%b %d, %H:%M"),
                }
                for n in notes
            ],
            "view_all_url": _notification_portal_url(request.user),
        }
    )
