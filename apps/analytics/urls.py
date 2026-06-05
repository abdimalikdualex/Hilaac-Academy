from django.urls import path

from .views import admin_dashboard

app_name = "analytics"

urlpatterns = [
    path("", admin_dashboard, name="dashboard"),
]
