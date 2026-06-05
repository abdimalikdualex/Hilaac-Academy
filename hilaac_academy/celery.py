import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hilaac_academy.settings")

app = Celery("hilaac_academy")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
