from django.urls import path

from . import instructor_views as v

app_name = "instructor"

urlpatterns = [
    path("", v.instructor_dashboard, name="dashboard"),
    path("courses/", v.instructor_courses, name="courses"),
    path("courses/add/", v.instructor_course_add, name="course_add"),
    path("courses/<int:level_id>/", v.instructor_level, name="level"),
    path("courses/<int:level_id>/edit/", v.instructor_course_edit, name="course_edit"),
    path("courses/<int:level_id>/publish/", v.instructor_course_publish, name="course_publish"),
    path("courses/<int:level_id>/archive/", v.instructor_course_archive, name="course_archive"),
    path("courses/<int:level_id>/students/", v.instructor_students, name="level_students"),
    path("modules/<int:module_id>/edit/", v.instructor_module_edit, name="module_edit"),
    path("modules/<int:module_id>/delete/", v.instructor_module_delete, name="module_delete"),
    path("modules/<int:module_id>/move/<str:direction>/", v.instructor_module_move, name="module_move"),
    path("courses/<int:level_id>/modules/add/", v.instructor_module_add, name="module_add"),
    path("modules/<int:module_id>/lessons/add/", v.instructor_lesson_add, name="lesson_add"),
    path("lessons/<int:lesson_id>/edit/", v.instructor_lesson_edit, name="lesson_edit"),
    path("lessons/<int:lesson_id>/preview/", v.instructor_lesson_preview, name="lesson_preview"),
    path("lessons/<int:lesson_id>/delete/", v.instructor_lesson_delete, name="lesson_delete"),
    path("lessons/<int:lesson_id>/move/<str:direction>/", v.instructor_lesson_move, name="lesson_move"),
    path("assignments/", v.instructor_assignments, name="assignments"),
    path("assignments/submissions/<int:pk>/grade/", v.instructor_submission_grade, name="submission_grade"),
    path("modules/<int:module_id>/assignments/add/", v.instructor_assignment_add, name="assignment_add"),
    path("assignments/<int:pk>/edit/", v.instructor_assignment_edit, name="assignment_edit"),
    path("assignments/<int:pk>/delete/", v.instructor_assignment_delete, name="assignment_delete"),
    path("assignments/<int:pk>/publish/", v.instructor_assignment_toggle_publish, name="assignment_toggle_publish"),
    path("assignments/<int:pk>/extend-due/", v.instructor_assignment_extend_due, name="assignment_extend_due"),
    path("modules/<int:module_id>/quizzes/add/", v.instructor_quiz_add, name="quiz_add"),
    path("quizzes/<int:pk>/edit/", v.instructor_quiz_edit, name="quiz_edit"),
    path("quizzes/<int:pk>/delete/", v.instructor_quiz_delete, name="quiz_delete"),
    path("quizzes/<int:pk>/publish/", v.instructor_quiz_toggle_publish, name="quiz_toggle_publish"),
    path("quizzes/", v.instructor_quizzes, name="quizzes"),
    path("students/", v.instructor_students_all, name="students"),
    path("analytics/", v.instructor_analytics, name="analytics"),
    path("notifications/", v.instructor_notifications, name="notifications"),
    path("profile/", v.instructor_profile, name="profile"),
    path("settings/", v.instructor_settings, name="settings"),
    path("settings/password/", v.InstructorPasswordChangeView.as_view(), name="password_change"),
]
