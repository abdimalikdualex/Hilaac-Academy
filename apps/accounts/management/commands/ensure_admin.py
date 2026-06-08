from decouple import config
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User


class Command(BaseCommand):
    help = (
        "Create or reset the super admin account. "
        "Runs automatically on deploy when ADMIN_PASSWORD is set."
    )

    def add_arguments(self, parser):
        parser.add_argument("--username", default="")
        parser.add_argument("--email", default="")
        parser.add_argument("--password", default="")
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Reset password and super-admin flags for an existing user.",
        )

    def handle(self, *args, **options):
        username = options["username"] or config("ADMIN_USERNAME", default="admin")
        email = options["email"] or config("ADMIN_EMAIL", default="admin@hilaacacademy.com")
        password = options["password"] or config("ADMIN_PASSWORD", default="")
        reset = options["reset"]

        user = User.objects.filter(username__iexact=username).first()
        has_super_admin = User.objects.filter(role=User.Role.SUPER_ADMIN).exists()

        if user:
            if not reset and not password:
                self.stdout.write(
                    self.style.WARNING(
                        f"User '{user.username}' already exists. "
                        "Use --reset or set ADMIN_PASSWORD to update the password."
                    )
                )
                return
            if not password:
                raise CommandError("Provide --password or set the ADMIN_PASSWORD environment variable.")
            user.set_password(password)
            user.role = User.Role.SUPER_ADMIN
            user.is_staff = True
            user.is_superuser = True
            user.is_verified = True
            user.is_active = True
            if email and not user.email:
                user.email = email
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Updated super admin '{user.username}'."))
            return

        if has_super_admin and not reset:
            self.stdout.write(
                self.style.WARNING(
                    "A super admin already exists. "
                    f"Use --reset --username {username} to replace or update credentials."
                )
            )
            return

        if not password:
            self.stdout.write(
                self.style.WARNING(
                    "No super admin found and ADMIN_PASSWORD is not set. Skipping admin creation."
                )
            )
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        self.stdout.write(self.style.SUCCESS(f"Created super admin '{username}'."))
