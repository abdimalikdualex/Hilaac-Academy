"""Role helpers for dashboard routing and access control."""
from django.urls import reverse


def role_dashboard_url(user):
    if user.is_super_admin:
        return reverse("admin_portal:dashboard")
    if user.is_instructor:
        return reverse("instructor:dashboard")
    return reverse("student:dashboard")


def role_dashboard_name(user):
    if user.is_super_admin:
        return "admin_portal:dashboard"
    if user.is_instructor:
        return "instructor:dashboard"
    return "student:dashboard"
