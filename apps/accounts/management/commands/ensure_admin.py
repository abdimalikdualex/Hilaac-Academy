from decouple import config
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User


class Command(BaseCommand):
    help = (
        "Create the super admin if missing, or reset credentials with --reset. "
        "Deploy scripts never overwrite an existing admin unless --reset is passed."
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
            if not reset:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Super admin '{user.username}' already exists — credentials unchanged."
                    )
                )
                return
            if not password:
                raise CommandError(
                    "Provide --password or set ADMIN_PASSWORD when using --reset."
                )
            user.set_password(password)
            user.role = User.Role.SUPER_ADMIN
            user.is_staff = True
            user.is_superuser = True
            user.is_verified = True
            user.is_active = True
            if email:
                user.email = email
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Reset super admin '{user.username}'."))
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
