from django.urls import re_path

from .protected_media import serve_protected_media

app_name = "core"

urlpatterns = [
    re_path(r"^(?P<path>.+)$", serve_protected_media, name="protected_media"),
]
