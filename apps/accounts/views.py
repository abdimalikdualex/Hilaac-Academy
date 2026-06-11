from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordChangeView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from django.core.cache import cache

from apps.core.roles import role_dashboard_url
from apps.core.utils import get_client_ip, log_audit, rate_limit
from apps.notifications.services import send_verification_email

from .forms import HilaacAuthenticationForm, HilaacPasswordChangeForm, StudentRegistrationForm
from .models import User


class StudentLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = HilaacAuthenticationForm
    redirect_authenticated_user = True
    LOGIN_RATE_LIMIT = 10
    LOGIN_RATE_PERIOD = 300

    def post(self, request, *args, **kwargs):
        ip = get_client_ip(request) or "unknown"
        cache_key = f"ratelimit:login:{ip}"
        try:
            count = cache.get(cache_key, 0)
        except Exception:
            count = 0
        if count >= self.LOGIN_RATE_LIMIT:
            messages.error(
                request,
                "Too many login attempts. Please wait a few minutes and try again.",
            )
            return self.get(request)
        try:
            cache.set(cache_key, count + 1, self.LOGIN_RATE_PERIOD)
        except Exception:
            pass
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        return role_dashboard_url(self.request.user)

    def form_valid(self, form):
        response = super().form_valid(form)
        log_audit(self.request, "user_login", "User", self.request.user.pk)
        return response

    def form_invalid(self, form):
        username = self.request.POST.get("username", "").strip()
        if username:
            try:
                user = User.objects.get(username__iexact=username)
                if not user.is_active:
                    messages.error(request, "This account is deactivated. Contact support.")
            except User.DoesNotExist:
                pass
        return super().form_invalid(form)


class StudentLogoutView(LogoutView):
    next_page = reverse_lazy("cms:home")


@rate_limit("register", limit=5, period=600)
def register(request):
    if request.user.is_authenticated:
        return redirect(role_dashboard_url(request.user))

    if request.method == "POST":
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            if settings.REQUIRE_EMAIL_VERIFICATION:
                send_verification_email(user)
                messages.success(request, "Account created! Check your email to verify your account.")
                return redirect("accounts:verify_notice")
            log_audit(request, "user_register", "User", user.pk, user.email)
            messages.success(request, "Account created! You can log in now.")
            return redirect("accounts:login")
    else:
        form = StudentRegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


def verify_notice(request):
    if not settings.REQUIRE_EMAIL_VERIFICATION:
        if request.user.is_authenticated:
            return redirect(role_dashboard_url(request.user))
        return redirect("accounts:login")
    return render(request, "accounts/verify_notice.html")


def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        user.is_verified = True
        user.save(update_fields=["is_verified"])
        messages.success(request, "Email verified successfully! You can now log in.")
        return redirect("accounts:login")

    messages.error(request, "Invalid or expired verification link.")
    return redirect("accounts:verify_notice")


@login_required
def resend_verification(request):
    if request.user.is_verified:
        return redirect(role_dashboard_url(request.user))
    send_verification_email(request.user)
    messages.success(request, "Verification email sent again.")
    return redirect("accounts:verify_notice")


@login_required
def dashboard(request):
    return redirect(role_dashboard_url(request.user))


@login_required
def profile(request):
    if request.user.is_super_admin:
        return redirect("admin_portal:profile")
    if request.user.is_instructor:
        return redirect("instructor:profile")
    return redirect("student:profile")


class StudentPasswordChangeView(PasswordChangeView):
    form_class = HilaacPasswordChangeForm
    template_name = "accounts/password_change.html"

    def get_success_url(self):
        return role_dashboard_url(self.request.user)

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_super_admin:
                return redirect("admin_portal:profile_security")
            if request.user.is_instructor:
                return redirect("instructor:password_change")
            if request.user.is_student:
                return redirect("student:password_change")
        return super().dispatch(request, *args, **kwargs)


class StudentPasswordResetView(PasswordResetView):
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/email/password_reset_email.txt"
    html_email_template_name = "accounts/email/password_reset_email.html"
    subject_template_name = "accounts/email/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")


class StudentPasswordResetDoneView(PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class StudentPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")


class StudentPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"
