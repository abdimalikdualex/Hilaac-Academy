from django.contrib import admin

from .models import DiscussionReply, DiscussionThread, LiveClassSession


class DiscussionReplyInline(admin.TabularInline):
    model = DiscussionReply
    extra = 0


@admin.register(DiscussionThread)
class DiscussionThreadAdmin(admin.ModelAdmin):
    list_display = ("title", "level", "author", "is_pinned", "is_locked", "created_at")
    list_filter = ("is_pinned", "level")
    search_fields = ("title", "body")
    inlines = [DiscussionReplyInline]


@admin.register(LiveClassSession)
class LiveClassSessionAdmin(admin.ModelAdmin):
    list_display = ("title", "level", "starts_at", "platform", "is_published")
    list_filter = ("platform", "is_published", "level")
