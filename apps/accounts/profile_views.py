"""Shared profile view helpers — users may only edit their own profile."""
from django.contrib import messages
from django.shortcuts import redirect

from apps.core.utils import log_audit

from .forms import (
    AccountSettingsForm,
    AdminProfileForm,
    InstructorProfileForm,
    NotificationPreferencesForm,
    StudentProfileForm,
)
from .profile_helpers import profile_stats_for_user, security_logs_for_user


def _profile_form_for_user(user):
    if user.is_instructor:
        return InstructorProfileForm
    if user.is_super_admin:
        return AdminProfileForm
    return StudentProfileForm


def handle_profile_update(request, redirect_url):
    user = request.user
    if request.method == "POST" and request.POST.get("remove_photo"):
        if user.profile_photo:
            user.profile_photo.delete(save=False)
            user.profile_photo = None
            user.save(update_fields=["profile_photo"])
            log_audit(request, "profile_photo_remove", "User", user.pk)
            messages.success(request, "Profile photo removed.")
        return redirect(redirect_url)

    form_class = _profile_form_for_user(user)
    if request.method == "POST":
        form = form_class(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            log_audit(request, "profile_update", "User", user.pk, "personal information")
            messages.success(request, "Profile updated successfully.")
            return redirect(redirect_url)
    else:
        form = form_class(instance=user)

    return {
        "form": form,
        "profile_stats": profile_stats_for_user(user),
        "security_logs": security_logs_for_user(user),
    }


def handle_account_settings(request, redirect_url):
    user = request.user
    if request.method == "POST":
        form = AccountSettingsForm(request.POST, instance=user)
        if form.is_valid():
            old_email = user.email
            form.save()
            if old_email != user.email:
                log_audit(request, "profile_email_change", "User", user.pk, f"{old_email} -> {user.email}")
            else:
                log_audit(request, "profile_account_update", "User", user.pk)
            messages.success(request, "Account settings saved.")
            return redirect(redirect_url)
    else:
        form = AccountSettingsForm(instance=user)
    return {"account_form": form}


def handle_notification_settings(request, redirect_url):
    user = request.user
    if request.method == "POST":
        form = NotificationPreferencesForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            log_audit(request, "profile_notifications_update", "User", user.pk)
            messages.success(request, "Notification preferences saved.")
            return redirect(redirect_url)
    else:
        form = NotificationPreferencesForm(instance=user)
    return {"notification_form": form}
