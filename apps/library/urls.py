from django.urls import path

from .views import library_home

app_name = "library"

urlpatterns = [
    path("", library_home, name="home"),
]
