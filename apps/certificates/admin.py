from django.contrib import admin

from .models import Certificate


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("certificate_id", "student", "level", "issued_at")
    search_fields = ("certificate_id", "student__email", "student__username")
    readonly_fields = ("certificate_id", "issued_at")
