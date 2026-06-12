"""Shared password change view behavior for all portals."""
from django.contrib import messages
from django.contrib.auth.views import PasswordChangeView

from apps.core.utils import log_audit
from apps.notifications.services import notify_password_changed

from .forms import HilaacPasswordChangeForm
from .password_sessions import logout_other_sessions

PASSWORD_SUCCESS_MESSAGE = "Your password has been changed successfully."


class PortalPasswordChangeView(PasswordChangeView):
    form_class = HilaacPasswordChangeForm

    def form_valid(self, form):
        response = super().form_valid(form)
        logout_other_sessions(self.request.user, self.request.session.session_key)
        log_audit(self.request, "profile_password_change", "User", self.request.user.pk)
        notify_password_changed(self.request.user)
        messages.success(self.request, PASSWORD_SUCCESS_MESSAGE)
        return response
