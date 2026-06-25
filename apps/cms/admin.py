from django.contrib import admin

from .models import FAQ, LegalPage, SiteStatistic, Testimonial


@admin.register(LegalPage)
class LegalPageAdmin(admin.ModelAdmin):
    list_display = ("title", "page_type", "last_updated", "updated_at")
    readonly_fields = ("page_type", "last_updated", "created_at", "updated_at")


@admin.register(SiteStatistic)
class SiteStatisticAdmin(admin.ModelAdmin):
    list_display = ("label", "value", "order", "is_active")


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("student_name", "course_name", "rating", "is_featured", "order")


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "order", "is_active")
