from django.contrib import admin

from .models import LessonProgress


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ("student", "lesson", "watched_seconds", "is_completed", "last_watched_at")
    list_filter = ("is_completed",)
