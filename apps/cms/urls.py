from django.urls import path

from .views import home, legal_page, platform_video_track

app_name = "cms"

urlpatterns = [
    path("", home, name="home"),
    path("privacy-policy/", legal_page, {"page_type": "privacy"}, name="privacy_policy"),
    path("terms-conditions/", legal_page, {"page_type": "terms"}, name="terms_conditions"),
    path("platform-video/track/", platform_video_track, name="platform_video_track"),
]
