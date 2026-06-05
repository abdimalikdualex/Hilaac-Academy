from django.urls import path

from .views import take_quiz

app_name = "assessments"

urlpatterns = [
    path("<int:quiz_id>/", take_quiz, name="take_quiz"),
]
