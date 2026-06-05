from django.urls import path

from .views import (
    StudentLoginView,
    StudentLogoutView,
    StudentPasswordChangeView,
    StudentPasswordResetCompleteView,
    StudentPasswordResetConfirmView,
    StudentPasswordResetDoneView,
    StudentPasswordResetView,
    dashboard,
    profile,
    register,
    resend_verification,
    verify_email,
    verify_notice,
)

app_name = "accounts"

urlpatterns = [
    path("register/", register, name="register"),
    path("login/", StudentLoginView.as_view(), name="login"),
    path("logout/", StudentLogoutView.as_view(), name="logout"),
    path("dashboard/", dashboard, name="dashboard"),
    path("profile/", profile, name="profile"),
    path("password/change/", StudentPasswordChangeView.as_view(), name="password_change"),
    path("password/reset/", StudentPasswordResetView.as_view(), name="password_reset"),
    path("password/reset/done/", StudentPasswordResetDoneView.as_view(), name="password_reset_done"),
    path("password/reset/<uidb64>/<token>/", StudentPasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("password/reset/complete/", StudentPasswordResetCompleteView.as_view(), name="password_reset_complete"),
    path("verify/", verify_notice, name="verify_notice"),
    path("verify/<uidb64>/<token>/", verify_email, name="verify_email"),
    path("verify/resend/", resend_verification, name="resend_verification"),
]
