from django.urls import path

from .views import download_certificate, my_certificates, verify

app_name = "certificates"

urlpatterns = [
    path("verify/<str:certificate_id>/", verify, name="verify"),
    path("my/", my_certificates, name="list"),
    path("download/<str:certificate_id>/", download_certificate, name="download"),
]
