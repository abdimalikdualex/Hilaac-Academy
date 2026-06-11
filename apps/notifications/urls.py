from django.urls import path

from .views import delete_notification, mark_read, mark_read_api, notification_list, recent_dropdown

app_name = "notifications"

urlpatterns = [
    path("", notification_list, name="list"),
    path("recent/", recent_dropdown, name="recent"),
    path("<int:pk>/read/", mark_read, name="mark_read"),
    path("<int:pk>/read-api/", mark_read_api, name="mark_read_api"),
    path("<int:pk>/delete/", delete_notification, name="delete"),
]
