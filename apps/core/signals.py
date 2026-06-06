from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.core.cache_sync import invalidate_platform_cache

# Models whose changes must reflect immediately across the platform.
SYNC_MODELS = set()


def register_cache_sync(model):
    SYNC_MODELS.add(model)
    return model


def _invalidate(sender, **kwargs):
    if sender in SYNC_MODELS:
        invalidate_platform_cache()


def connect_cache_signals():
    for model in SYNC_MODELS:
        post_save.connect(_invalidate, sender=model, weak=False)
        post_delete.connect(_invalidate, sender=model, weak=False)
