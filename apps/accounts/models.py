import os

from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models
from django.utils import timezone


def profile_photo_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        ext = ".jpg"
    timestamp = int(timezone.now().timestamp())
    user_id = instance.pk or "new"
    return f"profile_photos/{user_id}_{timestamp}{ext}"


class UserManager(DjangoUserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", "super_admin")
        extra_fields.setdefault("is_verified", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Admin"
        INSTRUCTOR = "instructor", "Instructor"
        STUDENT = "student", "Student"

    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"

    class LanguagePreference(models.TextChoices):
        ENGLISH = "en", "English"
        KISWAHILI = "sw", "Kiswahili"
        SOMALI = "so", "Somali"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    phone = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    profile_photo = models.ImageField(upload_to=profile_photo_upload_path, blank=True, null=True)
    language_preference = models.CharField(
        max_length=5,
        choices=LanguagePreference.choices,
        default=LanguagePreference.ENGLISH,
    )
    is_verified = models.BooleanField(default=False)
    bio = models.TextField(blank=True, help_text="Instructor biography")
    teaching_experience = models.TextField(blank=True)
    specialization = models.CharField(max_length=200, blank=True)
    skills = models.CharField(max_length=300, blank=True, help_text="Comma-separated skills")
    certifications = models.TextField(blank=True)
    linkedin_url = models.URLField(blank=True)
    website_url = models.URLField(blank=True)
    notify_course_updates = models.BooleanField(default=True)
    notify_assignments = models.BooleanField(default=True)
    notify_certificates = models.BooleanField(default=True)
    notify_marketing = models.BooleanField(default=False)
    notify_system = models.BooleanField(default=True)

    objects = UserManager()

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self):
        return self.get_full_name() or self.email or self.username

    @property
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN or self.is_superuser

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_instructor(self):
        return self.role == self.Role.INSTRUCTOR

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.profile_photo:
            from apps.core.imaging import IMAGE_PRESETS, optimize_image_field

            optimize_image_field(
                self.profile_photo,
                max_size=IMAGE_PRESETS["profile_photo"]["full"],
                preset="profile_photo",
            )
