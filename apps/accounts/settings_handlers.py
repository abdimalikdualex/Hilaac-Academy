"""Unified Settings page — profile, account info, and password on one page."""
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import redirect

from apps.core.utils import log_audit

from .forms import HilaacPasswordChangeForm, SettingsProfileForm
from .password_sessions import logout_other_sessions
from .password_views import PASSWORD_SUCCESS_MESSAGE

SETTINGS_SUCCESS = "Changes saved successfully."


def _settings_form_for_user(user):
    return SettingsProfileForm


def unified_settings_context(request, password_form=None):
    user = request.user
    form_class = _settings_form_for_user(user)
    return {
        "form": form_class(instance=user),
        "password_form": password_form or HilaacPasswordChangeForm(user=user),
    }


def handle_unified_settings_post(request, redirect_name):
    user = request.user

    if request.POST.get("form_action") == "password":
        return _handle_password_post(request, redirect_name)

    form_class = _settings_form_for_user(user)

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
        form.save()
        log_audit(request, "profile_update", "User", user.pk)
        messages.success(request, SETTINGS_SUCCESS)
        return redirect(redirect_name)

    for field, errs in form.errors.items():
        label = form.fields.get(field).label if field in form.fields else field
        messages.error(request, f"{label}: {errs[0]}")
    return {"form": form}


def _handle_password_post(request, redirect_name):
    form = HilaacPasswordChangeForm(user=request.user, data=request.POST)
    if form.is_valid():
        form.save()
        update_session_auth_hash(request, request.user)
        logout_other_sessions(request.user, request.session.session_key)
        log_audit(request, "profile_password_change", "User", request.user.pk)
        from apps.notifications.services import notify_password_changed

        notify_password_changed(request.user)
        messages.success(request, PASSWORD_SUCCESS_MESSAGE)
        return redirect(redirect_name)

    for field, errs in form.errors.items():
        label = form.fields.get(field).label if field in form.fields else field
        messages.error(request, f"{label}: {errs[0]}")
    return {"password_form": form}
