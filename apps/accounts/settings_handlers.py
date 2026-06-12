"""Unified Settings page — personal info, account details, password."""
from django.contrib import messages
from django.shortcuts import redirect

from apps.core.utils import log_audit

from .profile_helpers import profile_stats_for_user, security_logs_for_user
from .profile_views import _profile_form_for_user

SETTINGS_SUCCESS = "Your settings have been updated successfully."


def unified_settings_context(request):
    user = request.user
    form_class = _profile_form_for_user(user)
    return {
        "form": form_class(instance=user),
        "profile_stats": profile_stats_for_user(user),
        "security_logs": security_logs_for_user(user),
        "settings_section": "personal",
    }


def handle_unified_settings_post(request, redirect_name):
    user = request.user
    form_class = _profile_form_for_user(user)

    if request.POST.get("remove_photo"):
        if user.profile_photo:
            user.profile_photo.delete(save=False)
            user.profile_photo = None
            user.save(update_fields=["profile_photo"])
            log_audit(request, "profile_photo_remove", "User", user.pk)
            messages.success(request, SETTINGS_SUCCESS)
        return redirect(redirect_name)

    form = form_class(request.POST, request.FILES, instance=user)
    if form.is_valid():
        old_email = user.email
        form.save()
        user.refresh_from_db()
        if old_email != user.email:
            log_audit(request, "profile_email_change", "User", user.pk, f"{old_email} -> {user.email}")
        else:
            log_audit(request, "profile_update", "User", user.pk)
        messages.success(request, SETTINGS_SUCCESS)
        return redirect(redirect_name)

    for field, errs in form.errors.items():
        label = form.fields.get(field).label if field in form.fields else field
        messages.error(request, f"{label}: {errs[0]}")
    return None


PREFERENCES_SUCCESS = "Your preferences have been updated successfully."


def preferences_context(request):
    from .forms import NotificationPreferencesForm

    return {
        "form": NotificationPreferencesForm(instance=request.user),
        "settings_section": "preferences",
    }


def handle_preferences_post(request, redirect_name):
    from .forms import NotificationPreferencesForm

    user = request.user
    form = NotificationPreferencesForm(request.POST, instance=user)
    if form.is_valid():
        form.save()
        log_audit(request, "profile_notifications_update", "User", user.pk)
        messages.success(request, PREFERENCES_SUCCESS)
        return redirect(redirect_name)
    for field, errs in form.errors.items():
        label = form.fields.get(field).label if field in form.fields else field
        messages.error(request, f"{label}: {errs[0]}")
    return None
