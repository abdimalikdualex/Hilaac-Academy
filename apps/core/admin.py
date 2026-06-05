from django.contrib import admin

from .models import AuditLog, SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "user", "model_name", "created_at")
    list_filter = ("action", "model_name", "created_at")
    search_fields = ("action", "details", "user__email")
    readonly_fields = ("user", "action", "model_name", "object_id", "details", "ip_address", "created_at")
