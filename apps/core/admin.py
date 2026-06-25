from django.contrib import admin



from .models import AuditLog, SiteSettings





@admin.register(SiteSettings)

class SiteSettingsAdmin(admin.ModelAdmin):

    def has_add_permission(self, request):

        return not SiteSettings.objects.exists()





@admin.register(AuditLog)

class AuditLogAdmin(admin.ModelAdmin):

    list_display = ("get_description", "get_performer", "get_module", "status", "created_at")

    list_filter = ("status", "module", "user_role", "created_at")

    search_fields = ("action", "description", "details", "user_display_name", "user__username")

    readonly_fields = (

        "user",

        "user_display_name",

        "user_role",

        "action",

        "module",

        "description",

        "model_name",

        "object_id",

        "details",

        "old_values",

        "new_values",

        "ip_address",

        "user_agent",

        "status",

        "created_at",

    )



    @admin.display(description="Action")

    def get_description(self, obj):

        return obj.description_display



    @admin.display(description="User")

    def get_performer(self, obj):

        return obj.performer_name



    @admin.display(description="Module")

    def get_module(self, obj):

        return obj.module_display



    def has_add_permission(self, request):

        return False



    def has_change_permission(self, request, obj=None):

        return False



    def has_delete_permission(self, request, obj=None):

        return False


