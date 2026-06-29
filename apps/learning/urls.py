from django.urls import path

from .views import ai_ask_course, ai_ask_lesson, course_view, lesson_player, update_progress

app_name = "learning"

urlpatterns = [
    path("courses/<int:level_id>/", course_view, name="course_view"),
    path("courses/<int:level_id>/ai-ask/", ai_ask_course, name="ai_ask_course"),
    path("lessons/<int:lesson_id>/", lesson_player, name="lesson_player"),
    path("lessons/<int:lesson_id>/ai-ask/", ai_ask_lesson, name="ai_ask_lesson"),
    path("lessons/<int:lesson_id>/progress/", update_progress, name="update_progress"),
]
