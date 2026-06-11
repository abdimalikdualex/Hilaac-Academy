from django.urls import path

from .views import assignment_detail, assignment_submit, take_quiz

app_name = "assessments"

urlpatterns = [
    path("assignments/<int:assignment_id>/", assignment_detail, name="assignment_detail"),
    path("assignments/<int:assignment_id>/submit/", assignment_submit, name="assignment_submit"),
    path("<int:quiz_id>/", take_quiz, name="take_quiz"),
]
