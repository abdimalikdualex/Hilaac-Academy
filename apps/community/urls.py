from django.urls import path

from . import views

app_name = "community"

urlpatterns = [
    path("courses/<int:level_id>/discussions/", views.course_discussions, name="course_discussions"),
    path("thread/<int:thread_id>/", views.thread_detail, name="thread_detail"),
    path("thread/<int:thread_id>/pin/", views.thread_pin, name="thread_pin"),
    path("live-classes/", views.live_classes, name="live_classes"),
    path("instructor/courses/<int:level_id>/live-sessions/", views.instructor_live_sessions, name="instructor_live_sessions"),
]
