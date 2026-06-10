from django.urls import path
from django.views.generic import RedirectView

from . import recycle_bin, views

app_name = "admin_portal"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    # Students
    path("students/", views.student_list, name="student_list"),
    path("students/add/", views.student_create, name="student_create"),
    path("students/<int:pk>/", views.student_detail, name="student_detail"),
    path("students/<int:pk>/edit/", views.student_edit, name="student_edit"),
    path("students/<int:pk>/toggle/", views.student_toggle_active, name="student_toggle"),
    path("students/<int:pk>/delete/", views.student_delete, name="student_delete"),
    # Instructors
    path("instructors/", views.instructor_list, name="instructor_list"),
    path("instructors/add/", views.instructor_create, name="instructor_create"),
    path("instructors/<int:pk>/edit/", views.instructor_edit, name="instructor_edit"),
    path("instructors/<int:pk>/delete/", views.instructor_delete, name="instructor_delete"),
    # Courses
    path("courses/", views.course_list, name="course_list"),
    path("courses/add/", views.course_create, name="course_create"),
    path("courses/<int:pk>/edit/", views.course_edit, name="course_edit"),
    path("courses/<int:pk>/publish/", views.course_toggle_publish, name="course_toggle_publish"),
    path("courses/<int:pk>/archive/", views.course_archive, name="course_archive"),
    path("courses/<int:pk>/delete/", views.course_delete, name="course_delete"),
    path("videos/", RedirectView.as_view(url="/admin-portal/courses/", permanent=False), name="videos"),
    # Enrollments
    path("enrollments/", views.enrollment_list, name="enrollment_list"),
    path("enrollments/add/", views.enrollment_create, name="enrollment_create"),
    path("enrollments/<int:pk>/delete/", views.enrollment_delete, name="enrollment_delete"),
    # Payments
    path("payments/", views.payment_list, name="payment_list"),
    path("payments/<int:pk>/approve/", views.payment_approve, name="payment_approve"),
    path("payments/<int:pk>/reject/", views.payment_reject, name="payment_reject"),
    path("payments/<int:pk>/refund/", views.payment_refund, name="payment_refund"),
    # Certificates
    path("certificates/", views.certificate_list, name="certificate_list"),
    path("certificates/<int:pk>/revoke/", views.certificate_revoke, name="certificate_revoke"),
    path("certificates/<int:pk>/delete/", views.certificate_delete, name="certificate_delete"),
    path("certificates/generate/", views.certificate_generate, name="certificate_generate"),
    # Quizzes & Assignments
    path("quizzes/", views.quiz_list, name="quiz_list"),
    path("quizzes/<int:pk>/delete/", views.quiz_delete, name="quiz_delete"),
    path("assignments/", views.assignment_list, name="assignment_list"),
    path("assignments/<int:pk>/delete/", views.assignment_delete, name="assignment_delete"),
    path("assignments/submissions/<int:pk>/grade/", views.submission_grade, name="submission_grade"),
    # Library
    path("library/", views.library_list, name="library_list"),
    path("library/add/", views.library_create, name="library_create"),
    path("library/<int:pk>/delete/", views.library_delete, name="library_delete"),
    # Reports & CMS
    path("reports/", views.reports, name="reports"),
    path("cms/", views.cms_home, name="cms_home"),
    path("cms/faq/add/", views.cms_faq_edit, {"pk": None}, name="cms_faq_add"),
    path("cms/faq/<int:pk>/edit/", views.cms_faq_edit, name="cms_faq_edit"),
    path("cms/faq/<int:pk>/delete/", views.faq_delete, name="faq_delete"),
  # Partner Schools
    path("platform-video/", views.platform_video_list, name="platform_video_list"),
    path("platform-video/add/", views.platform_video_edit, {"pk": None}, name="platform_video_add"),
    path("platform-video/<int:pk>/edit/", views.platform_video_edit, name="platform_video_edit"),
    path("platform-video/<int:pk>/toggle/", views.platform_video_toggle, name="platform_video_toggle"),
    path("platform-video/<int:pk>/delete/", views.platform_video_delete, name="platform_video_delete"),
    path("announcements/", views.announcement_list, name="announcement_list"),
    path("announcements/add/", views.announcement_add, name="announcement_add"),
    path("announcements/<int:pk>/edit/", views.announcement_edit, name="announcement_edit"),
    path("announcements/<int:pk>/toggle/", views.announcement_toggle, name="announcement_toggle"),
    path("announcements/<int:pk>/delete/", views.announcement_delete, name="announcement_delete"),
    path("partner-schools/", views.partner_school_list, name="partner_school_list"),
    path("partner-schools/add/", views.partner_school_edit, {"pk": None}, name="partner_school_add"),
    path("partner-schools/<int:pk>/edit/", views.partner_school_edit, name="partner_school_edit"),
    path("partner-schools/<int:pk>/toggle/", views.partner_school_toggle, name="partner_school_toggle"),
    path("partner-schools/<int:pk>/delete/", views.partner_school_delete, name="partner_school_delete"),
    path("notifications/", views.notification_list, name="notification_list"),
    path("settings/", views.settings_view, name="settings"),
    path("recycle-bin/", recycle_bin.recycle_bin_list, name="recycle_bin"),
    path("recycle-bin/<str:model_type>/<int:pk>/restore/", recycle_bin.recycle_bin_restore, name="recycle_bin_restore"),
    path("recycle-bin/<str:model_type>/<int:pk>/purge/", recycle_bin.recycle_bin_purge, name="recycle_bin_purge"),
    path("exchange-rates/", views.exchange_rates, name="exchange_rates"),
]
