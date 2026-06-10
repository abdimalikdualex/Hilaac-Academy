from django.urls import path

from .views import home, platform_video_track

app_name = "cms"

urlpatterns = [
    path("", home, name="home"),
    path("platform-video/track/", platform_video_track, name="platform_video_track"),
]
