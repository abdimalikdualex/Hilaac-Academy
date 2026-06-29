from django.urls import path

from . import student_views as v

app_name = "student"

urlpatterns = [
    path("", v.dashboard, name="dashboard"),
    path("dashboard-stats/", v.dashboard_stats_partial, name="dashboard_stats"),
    path("courses/", v.my_courses, name="courses"),
    path("continue/", v.continue_learning, name="continue"),
    path("progress/", v.progress, name="progress"),
    path("progress/<int:level_id>/", v.progress_course, name="progress_course"),
    path("assignments/", v.assignments, name="assignments"),
    path("quizzes/", v.quizzes, name="quizzes"),
    path("certificates/", v.certificates, name="certificates"),
    path("library/", v.library, name="library"),
    path("wishlist/", v.wishlist, name="wishlist"),
    path("notifications/", v.notifications, name="notifications"),
    path("profile/", v.profile, name="profile"),
    path("settings/", v.settings, name="settings"),
    path("settings/account/", v.account_info, name="account_info"),
    path("settings/password/", v.StudentPortalPasswordChangeView.as_view(), name="password_change"),
    path("settings/preferences/", v.preferences, name="preferences"),
]
