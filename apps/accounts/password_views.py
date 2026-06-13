"""Shared password change view behavior for all portals."""
from django.contrib import messages
from django.contrib.auth.views import PasswordChangeView
from django.http import HttpResponseRedirect
from django.urls import reverse

from apps.core.utils import log_audit
from apps.notifications.services import notify_password_changed

from .forms import HilaacPasswordChangeForm
from .password_sessions import logout_other_sessions

PASSWORD_SUCCESS_MESSAGE = "Your password has been changed successfully."


class PortalPasswordChangeView(PasswordChangeView):
    """Legacy password URL — always redirects to unified Settings page."""

    form_class = HilaacPasswordChangeForm
    settings_url_name = None

    def _settings_password_url(self):
        if not self.settings_url_name:
            return reverse("accounts:password_change")
        return reverse(self.settings_url_name) + "#change-password"

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(self._settings_password_url())

    def post(self, request, *args, **kwargs):
        return HttpResponseRedirect(self._settings_password_url())

    def form_valid(self, form):
        response = super().form_valid(form)
        logout_other_sessions(self.request.user, self.request.session.session_key)
        log_audit(self.request, "profile_password_change", "User", self.request.user.pk)
        notify_password_changed(self.request.user)
        messages.success(self.request, PASSWORD_SUCCESS_MESSAGE)
        return response
