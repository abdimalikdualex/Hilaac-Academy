from django.contrib import admin

from .models import LibraryResource


@admin.register(LibraryResource)
class LibraryResourceAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "language", "is_published")
    list_filter = ("category", "language", "is_published")
    search_fields = ("title", "description")
