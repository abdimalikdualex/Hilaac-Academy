from django.urls import path

from .views import course_view, lesson_player, update_progress

app_name = "learning"

urlpatterns = [
    path("courses/<int:level_id>/", course_view, name="course_view"),
    path("lessons/<int:lesson_id>/", lesson_player, name="lesson_player"),
    path("lessons/<int:lesson_id>/progress/", update_progress, name="update_progress"),
]
