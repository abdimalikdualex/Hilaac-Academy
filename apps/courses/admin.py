from django.contrib import admin
from django.utils.html import format_html

from .models import CourseReview, Enrollment, Language, Lesson, LessonResource, Level, Module, Wishlist


class LessonResourceInline(admin.TabularInline):
    model = LessonResource
    extra = 0
    fields = ("title", "resource_type", "file", "order")


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0
    ordering = ("order",)
    fields = ("order", "title", "lesson_type", "duration_minutes", "is_preview", "is_published")
    show_change_link = True


class ModuleInline(admin.TabularInline):
    model = Module
    extra = 0
    ordering = ("order",)


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ("name", "language", "price", "is_free", "is_published", "order", "lesson_count")
    list_filter = ("language", "is_free", "is_published")
    search_fields = ("name", "description", "keywords")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ModuleInline]

    @admin.display(description="Lessons")
    def lesson_count(self, obj):
        return obj.total_lessons


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("title", "level", "order", "lesson_count")
    list_filter = ("level__language", "level")
    search_fields = ("title", "level__name")
    inlines = [LessonInline]

    @admin.display(description="Lessons")
    def lesson_count(self, obj):
        return obj.lessons.count()


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "module", "lesson_type", "duration_minutes", "video_status", "is_preview", "is_published")
    list_filter = ("lesson_type", "is_preview", "is_published", "module__level__language", "module__level")
    search_fields = ("title", "content", "module__title", "module__level__name")
    inlines = [LessonResourceInline]
    fieldsets = (
        (None, {
            "fields": ("module", "title", "lesson_type", "order", "duration_minutes", "is_preview", "is_published"),
        }),
        ("Video lesson", {
            "classes": ("wide",),
            "description": (
                "Upload an MP4 file OR paste a video URL. "
                "Uploaded file takes priority. For large files, use Cloudinary (set keys in .env)."
            ),
            "fields": ("video_file", "video_url"),
        }),
        ("Other content", {
            "fields": ("content", "pdf_file", "audio_file"),
        }),
    )

    @admin.display(description="Video")
    def video_status(self, obj):
        if obj.video_file:
            return format_html('<span style="color:green">✓ File uploaded</span>')
        if obj.video_url:
            return format_html('<span style="color:blue">✓ URL set</span>')
        if obj.lesson_type == Lesson.LessonType.VIDEO:
            return format_html('<span style="color:red">✗ Missing video</span>')
        return "—"


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "level", "status", "enrolled_at", "completed_at")
    list_filter = ("status", "level__language")
    search_fields = ("student__email", "student__username", "level__name")


@admin.register(CourseReview)
class CourseReviewAdmin(admin.ModelAdmin):
    list_display = ("level", "student", "rating", "created_at")
    list_filter = ("rating", "level__language")
    search_fields = ("level__name", "student__username", "comment")


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("student", "level", "created_at")
    search_fields = ("student__username", "level__name")
