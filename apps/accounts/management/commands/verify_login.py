"""Test whether credentials work (for server troubleshooting)."""
from django.contrib.auth import authenticate
from django.core.management.base import BaseCommand

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Verify username/email + password without exposing the password in output."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--password", required=True)

    def handle(self, *args, **options):
        username = options["username"].strip()
        password = options["password"].strip()
        user = authenticate(username=username, password=password)
        if user:
            self.stdout.write(
                self.style.SUCCESS(
                    f"OK — '{username}' authenticated as {user.username} (role={user.role})."
                )
            )
            return
        exists = User.objects.filter(username__iexact=username).first() or User.objects.filter(
            email__iexact=username
        ).first()
        if not exists:
            self.stdout.write(self.style.ERROR(f"No user matching '{username}' (username or email)."))
        else:
            self.stdout.write(
                self.style.ERROR(
                    f"User '{exists.username}' exists but password did not match. "
                    "Run: python manage.py ensure_admin --reset --username ... --password ..."
                )
            )
