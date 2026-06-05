from django.urls import path

from .views import (
    catalog,
    course_detail,
    enroll,
    preview_lesson,
    submit_review,
    toggle_wishlist,
)

app_name = "courses"

urlpatterns = [
    path("", catalog, name="catalog"),
    path("lesson/<int:lesson_id>/preview/", preview_lesson, name="preview_lesson"),
    path("<int:level_id>/enroll/", enroll, name="enroll"),
    path("<int:level_id>/review/", submit_review, name="submit_review"),
    path("<int:level_id>/wishlist/", toggle_wishlist, name="toggle_wishlist"),
    path("<slug:language_slug>/<slug:level_slug>/", course_detail, name="detail"),
]
