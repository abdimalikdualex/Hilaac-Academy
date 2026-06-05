from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.accounts.signals import sync_user_role_group


class Command(BaseCommand):
    help = "Sync all users into Django Groups based on their role."

    def handle(self, *args, **options):
        count = 0
        for user in User.objects.all():
            sync_user_role_group(user)
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Synced {count} users into role groups."))
