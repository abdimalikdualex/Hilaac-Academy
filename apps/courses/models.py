from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from apps.core.models import TimeStampedModel


class Language(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Level(TimeStampedModel):
    class LevelTag(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    language = models.ForeignKey(Language, on_delete=models.CASCADE, related_name="levels")
    name = models.CharField(max_length=100, help_text="Course title, e.g. English Beginner")
    subtitle = models.CharField(max_length=200, blank=True, help_text="Short tagline shown under the title")
    level_tag = models.CharField(max_length=20, choices=LevelTag.choices, blank=True, help_text="Difficulty level")
    slug = models.SlugField(blank=True)
    order = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    learning_objectives = models.TextField(blank=True, help_text="One objective per line")
    skills = models.TextField(blank=True, help_text="Skills students acquire, one per line")
    target_audience = models.TextField(blank=True, help_text="Who this course is for, one per line")
    requirements = models.TextField(blank=True, help_text="Course requirements, one per line")
    keywords = models.CharField(max_length=500, blank=True, help_text="Comma-separated search keywords")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_free = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    certificate_included = models.BooleanField(default=True, help_text="Show 'Certificate included' on the course page")
    duration_weeks = models.PositiveIntegerField(default=4, help_text="Estimated duration in weeks")
    thumbnail = models.ImageField(
        upload_to="courses/covers/",
        blank=True,
        null=True,
        help_text="Course cover image. Recommended 1280x720 (JPG, PNG or WEBP).",
    )
    banner = models.ImageField(
        upload_to="courses/banners/",
        blank=True,
        null=True,
        help_text="Optional wide banner image shown on the course page.",
    )
    instructor = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_levels",
        limit_choices_to={"role": "instructor"},
    )

    class Meta:
        ordering = ["language", "order"]
        unique_together = ("language", "slug")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if self.is_free:
            self.price = 0
        super().save(*args, **kwargs)
        if self.thumbnail or self.banner:
            from apps.core.imaging import COVER_MAX_SIZE, optimize_image_field

            if self.thumbnail:
                optimize_image_field(self.thumbnail, max_size=COVER_MAX_SIZE)
            if self.banner:
                optimize_image_field(self.banner, max_size=(1920, 480))

    def __str__(self):
        return f"{self.language.name} - {self.name}"

    def get_absolute_url(self):
        return reverse("courses:detail", kwargs={"language_slug": self.language.slug, "level_slug": self.slug})

    @property
    def total_lessons(self):
        return Lesson.objects.filter(module__level=self, is_published=True).count()

    @property
    def cover_url(self):
        """Always return a usable cover image URL (uploaded or placeholder)."""
        if self.thumbnail:
            return self.thumbnail.url
        from apps.core.imaging import static_url

        return static_url("images/course-placeholder.svg")

    @property
    def banner_url(self):
        """Banner image URL, falling back to the cover image."""
        if self.banner:
            return self.banner.url
        return self.cover_url

    @property
    def status_label(self):
        if self.is_archived:
            return "Archived"
        return "Published" if self.is_published else "Draft"

    @property
    def total_modules(self):
        return self.modules.count()

    @property
    def total_assessments(self):
        from apps.assessments.models import Assignment, Quiz

        quizzes = Quiz.objects.filter(
            models.Q(level=self) | models.Q(module__level=self)
        ).distinct().count()
        assignments = Assignment.objects.filter(module__level=self).count()
        return quizzes + assignments

    @property
    def enrollment_count(self):
        return self.enrollments.count()

    @property
    def review_count(self):
        return self.reviews.count()

    @property
    def average_rating(self):
        from django.db.models import Avg

        avg = self.reviews.aggregate(a=Avg("rating"))["a"]
        return round(avg, 1) if avg else 0

    @property
    def has_preview(self):
        return Lesson.objects.filter(module__level=self, is_preview=True, is_published=True).exists()

    @property
    def total_duration_minutes(self):
        return (
            Lesson.objects.filter(module__level=self, is_published=True)
            .aggregate(total=models.Sum("duration_minutes"))["total"]
            or 0
        )

    @property
    def preview_lesson_count(self):
        return Lesson.objects.filter(module__level=self, is_preview=True, is_published=True).count()

    @property
    def first_preview_lesson(self):
        from .preview import get_first_preview_lesson

        return get_first_preview_lesson(self)


class Module(TimeStampedModel):
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["level", "order"]

    def __str__(self):
        return f"{self.level} - {self.title}"

    @property
    def total_lessons(self):
        return self.lessons.filter(is_published=True).count()

    @property
    def total_duration_minutes(self):
        return self.lessons.filter(is_published=True).aggregate(
            total=models.Sum("duration_minutes")
        )["total"] or 0


class Lesson(TimeStampedModel):
    class LessonType(models.TextChoices):
        VIDEO = "video", "Video"
        PDF = "pdf", "PDF Notes"
        AUDIO = "audio", "Audio"
        READING = "reading", "Reading Material"
        VOCABULARY = "vocabulary", "Vocabulary Exercise"

    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, help_text="Short lesson summary shown to students.")
    lesson_type = models.CharField(max_length=20, choices=LessonType.choices, default=LessonType.VIDEO)
    content = models.TextField(blank=True, help_text="Lesson notes, instructions, or reading text.")
    video_file = models.FileField(
        upload_to="lessons/videos/",
        blank=True,
        null=True,
        help_text="Upload MP4 video directly (recommended). Used before video URL if both are set.",
    )
    video_url = models.URLField(
        blank=True,
        help_text="Or paste a video URL (YouTube, Vimeo, Cloudinary, etc.) if not uploading a file.",
    )
    thumbnail = models.ImageField(
        upload_to="lessons/thumbnails/",
        blank=True,
        null=True,
        help_text="Video preview thumbnail. Auto-captured from the video or upload your own.",
    )
    audio_file = models.FileField(upload_to="lessons/audio/", blank=True, null=True)
    pdf_file = models.FileField(upload_to="lessons/pdf/", blank=True, null=True)
    duration_minutes = models.PositiveIntegerField(default=10)
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)
    is_preview = models.BooleanField(
        default=False,
        help_text="Free preview: only the first lesson in the course may be marked (max 1).",
    )
    preview_views = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        ordering = ["module", "order"]

    def clean(self):
        super().clean()
        from .preview import validate_preview_lesson

        validate_preview_lesson(self)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.thumbnail:
            from apps.core.imaging import THUMB_MAX_SIZE, optimize_image_field

            optimize_image_field(self.thumbnail, max_size=THUMB_MAX_SIZE)

    def __str__(self):
        return self.title

    @property
    def playable_video_url(self):
        """Return the best available video source for the lesson player."""
        if self.video_file:
            return self.video_file.url
        return self.video_url or ""

    @property
    def thumbnail_url(self):
        """Always return a usable thumbnail URL (uploaded or placeholder)."""
        if self.thumbnail:
            return self.thumbnail.url
        from apps.core.imaging import static_url

        return static_url("images/lesson-placeholder.svg")

    @property
    def type_icon(self):
        """Lucide icon name for templates ({% ha_icon lesson.type_icon %})."""
        from apps.core.brand_assets import BrandAssetManager

        return BrandAssetManager.lesson_icon(self.lesson_type)

    @property
    def video_filesize_display(self):
        """Human-readable size of the uploaded video file, if any."""
        if not self.video_file:
            return ""
        try:
            size = self.video_file.size
        except Exception:
            return ""
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024 or unit == "GB":
                return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
            size /= 1024
        return ""


class LessonResource(TimeStampedModel):
    """Downloadable files attached to a lesson (PDF, DOCX, worksheets, etc.)."""

    class ResourceType(models.TextChoices):
        PDF = "pdf", "PDF"
        DOCX = "docx", "Word Document"
        PPTX = "pptx", "Presentation"
        AUDIO = "audio", "Audio"
        ZIP = "zip", "ZIP Archive"
        OTHER = "other", "Other"

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="resources")
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to="lessons/resources/")
    resource_type = models.CharField(max_length=10, choices=ResourceType.choices, default=ResourceType.PDF)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["lesson", "order"]

    def __str__(self):
        return f"{self.lesson.title} — {self.title}"


class Enrollment(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    student = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="enrollments")
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name="enrollments")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("student", "level")
        ordering = ["-enrolled_at"]

    def __str__(self):
        return f"{self.student} - {self.level}"

    @property
    def progress_percentage(self):
        from apps.learning.models import LessonProgress

        total = self.level.total_lessons
        if total == 0:
            return 0
        completed = LessonProgress.objects.filter(
            student=self.student,
            lesson__module__level=self.level,
            is_completed=True,
        ).count()
        return round((completed / total) * 100)


class CourseReview(TimeStampedModel):
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name="reviews")
    student = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="course_reviews")
    rating = models.PositiveSmallIntegerField(default=5, help_text="1 to 5 stars")
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = ("level", "student")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student} → {self.level} ({self.rating}/5)"


class Wishlist(TimeStampedModel):
    student = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="wishlist_items")
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name="wishlisted_by")

    class Meta:
        unique_together = ("student", "level")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student} — {self.level} (wishlist)"
