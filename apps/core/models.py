from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditLog(models.Model):
    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    user_display_name = models.CharField(max_length=200, blank=True)
    user_role = models.CharField(max_length=20, blank=True)
    action = models.CharField(max_length=100, db_index=True)
    module = models.CharField(max_length=50, blank=True, db_index=True)
    description = models.TextField(blank=True)
    model_name = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    details = models.TextField(blank=True)
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.SUCCESS,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at", "module"]),
            models.Index(fields=["user_role", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.action} - {self.created_at:%Y-%m-%d %H:%M}"

    @property
    def performer_name(self):
        if self.user_id:
            return self.user.get_full_name() or self.user.username
        if self.user_display_name:
            return self.user_display_name
        return "Deleted User"

    @property
    def performer_username(self):
        if self.user_id:
            return self.user.username
        return "—"

    @property
    def performer_role_display(self):
        if self.user_id:
            return self.user.get_role_display()
        if self.user_role:
            from apps.accounts.models import User

            return dict(User.Role.choices).get(self.user_role, self.user_role)
        return "—"

    @property
    def module_display(self):
        if self.module:
            return self.module
        from .audit_service import resolve_module

        return resolve_module(self.action, self.model_name)

    @property
    def description_display(self):
        if self.description:
            return self.description
        from .audit_service import format_description

        return format_description(self.action, self.details, self.model_name, self.object_id)


class SiteSettings(models.Model):
    """Singleton settings for Hilaac Academy (single-tenant V1)."""

    academy_name = models.CharField(max_length=200, default="Hilaac Academy")
    tagline = models.CharField(max_length=300, default="Baro Xirfado Casri ah, Dhis Mustaqbalkaaga")
    logo = models.ImageField(upload_to="site/", blank=True, null=True)
    banner = models.ImageField(upload_to="site/", blank=True, null=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    contact_address = models.CharField(max_length=300, blank=True)
    facebook_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    whatsapp_number = models.CharField(max_length=30, blank=True)
    footer_text = models.TextField(blank=True)
    demo_content_seeded = models.BooleanField(
        default=False,
        help_text="Set after first demo seed so deploys never restore deleted demo courses.",
    )

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return self.academy_name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
