"""Permanently delete soft-deleted items older than the retention period."""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.soft_delete import RECYCLE_RETENTION_DAYS
from apps.courses.models import Lesson, Level, Module
from apps.library.models import LibraryResource


class Command(BaseCommand):
    help = f"Purge soft-deleted items older than {RECYCLE_RETENTION_DAYS} days"

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=RECYCLE_RETENTION_DAYS)
        purged = 0

        for model in (Lesson, Module, Level, LibraryResource):
            stale = model.all_objects.filter(is_deleted=True, deleted_at__lt=cutoff)
            count = stale.count()
            if count:
                stale.delete()
                purged += count
                self.stdout.write(f"  Purged {count} {model.__name__}(s)")

        if purged:
            self.stdout.write(self.style.SUCCESS(f"Purged {purged} item(s) from recycle bin."))
        else:
            self.stdout.write("No expired items to purge.")
