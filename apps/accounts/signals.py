from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User

ROLE_GROUPS = {
    User.Role.STUDENT: "Students",
    User.Role.INSTRUCTOR: "Instructors",
    User.Role.SUPER_ADMIN: "Super Admins",
}


def sync_user_role_group(user):
    """Assign the user to the Django Group matching their role."""
    group_name = ROLE_GROUPS.get(user.role)
    if not group_name:
        return
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.set([group])


@receiver(post_save, sender=User)
def assign_role_group(sender, instance, **kwargs):
    if instance.pk:
        sync_user_role_group(instance)
