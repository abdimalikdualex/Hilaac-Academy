from django.urls import path

from .views import home

app_name = "cms"

urlpatterns = [
    path("", home, name="home"),
]
