from django.urls import path

from . import manage_views

app_name = "courses_manage"

urlpatterns = [
    path("", manage_views.course_manager, name="list"),
    path("<int:level_id>/", manage_views.level_detail, name="level_detail"),
    path("<int:level_id>/modules/add/", manage_views.module_add, name="module_add"),
    path("modules/<int:module_id>/edit/", manage_views.module_edit, name="module_edit"),
    path("modules/<int:module_id>/delete/", manage_views.module_delete, name="module_delete"),
    path("modules/<int:module_id>/move/<str:direction>/", manage_views.module_move, name="module_move"),
    path("modules/<int:module_id>/lessons/add/", manage_views.lesson_add, name="lesson_add"),
    path("lessons/<int:lesson_id>/edit/", manage_views.lesson_edit, name="lesson_edit"),
    path("lessons/<int:lesson_id>/preview/", manage_views.lesson_preview, name="lesson_preview"),
    path("lessons/<int:lesson_id>/delete/", manage_views.lesson_delete, name="lesson_delete"),
    path("lessons/<int:lesson_id>/move/<str:direction>/", manage_views.lesson_move, name="lesson_move"),
]
