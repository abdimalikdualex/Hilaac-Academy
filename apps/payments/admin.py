from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("student", "level", "amount", "method", "status", "reference", "created_at")
    list_filter = ("status", "method")
    search_fields = ("student__email", "reference", "receipt_number")
    actions = ["approve_payments"]

    @admin.action(description="Approve selected payments")
    def approve_payments(self, request, queryset):
        for payment in queryset.filter(status=Payment.Status.PENDING):
            payment.approve()
