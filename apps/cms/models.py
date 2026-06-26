from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.models import TimeStampedModel

ANNOUNCEMENT_THEME_COLORS = {
    "primary": ("#1E4D8F", "#FFFFFF"),
    "success": ("#0FAE9D", "#FFFFFF"),
    "discount": ("#D4A017", "#FFFFFF"),
    "urgent": ("#DC2626", "#FFFFFF"),
}

ANNOUNCEMENT_THEME_LABELS = {
    "primary": "Primary Blue",
    "success": "Success",
    "discount": "Discount",
    "urgent": "Urgent Notice",
}


class SiteStatistic(models.Model):
    label = models.CharField(max_length=100)
    value = models.PositiveIntegerField(default=0)
    icon = models.CharField(max_length=50, blank=True, help_text="Emoji or icon class")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.label}: {self.value}"


class Testimonial(TimeStampedModel):
    student_name = models.CharField(max_length=100)
    course_name = models.CharField(max_length=200)
    quote = models.TextField()
    photo = models.ImageField(upload_to="testimonials/", blank=True, null=True)
    rating = models.PositiveIntegerField(default=5)
    is_featured = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.student_name


class FAQ(TimeStampedModel):
    question = models.CharField(max_length=300)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return self.question


class PartnerSchool(TimeStampedModel):
    """Partner institution logo shown in the footer carousel."""

    name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to="partner_schools/")
    website_url = models.URLField(blank=True, help_text="Opens in a new tab when the logo is clicked.")
    country = models.CharField(max_length=100, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name = "Partner School"
        verbose_name_plural = "Partner Schools"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.logo:
            from apps.core.imaging import IMAGE_PRESETS, optimize_image_field

            optimize_image_field(
                self.logo,
                max_size=IMAGE_PRESETS["partner_logo"]["full"],
                preset="partner_logo",
            )

    @property
    def tooltip_text(self):
        if self.country:
            return f"{self.name} — {self.country}"
        return self.name


class AnnouncementQuerySet(models.QuerySet):
    def active_now(self):
        now = timezone.now()
        return self.filter(is_active=True).filter(
            Q(start_date__isnull=True) | Q(start_date__lte=now),
            Q(end_date__isnull=True) | Q(end_date__gte=now),
        )


class Announcement(TimeStampedModel):
    class Type(models.TextChoices):
        DISCOUNT = "discount", "Course Discount"
        NEW_COURSE = "new_course", "New Course Launch"
        REGISTRATION = "registration", "Registration Notice"
        SCHOLARSHIP = "scholarship", "Scholarship"
        SYSTEM = "system", "System Announcement"
        WELCOME_SOMALI = "welcome_somali", "Somali Welcome Message"

    title = models.CharField(max_length=200, blank=True, help_text="Optional short label for admin lists.")
    message = models.CharField(max_length=500, help_text="Text shown in the scrolling ticker.")
    announcement_type = models.CharField(
        max_length=30,
        choices=Type.choices,
        default=Type.SYSTEM,
    )
    background_color = models.CharField(max_length=7, default="#1E4D8F")
    text_color = models.CharField(max_length=7, default="#FFFFFF")
    link_url = models.URLField(blank=True, help_text="Optional — makes the announcement clickable.")
    start_date = models.DateTimeField(null=True, blank=True, help_text="Leave blank to show immediately.")
    end_date = models.DateTimeField(null=True, blank=True, help_text="Leave blank for no expiry.")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    objects = AnnouncementQuerySet.as_manager()

    class Meta:
        ordering = ["display_order", "-created_at"]
        verbose_name = "Announcement"
        verbose_name_plural = "Announcements"

    def __str__(self):
        return self.title or self.message[:60]

    @property
    def is_live(self):
        if not self.is_active:
            return False
        now = timezone.now()
        if self.start_date and self.start_date > now:
            return False
        if self.end_date and self.end_date < now:
            return False
        return True

    def get_theme_key(self):
        stored = (self.background_color or "").strip()
        if stored in ANNOUNCEMENT_THEME_COLORS:
            return stored
        for key, (bg, _) in ANNOUNCEMENT_THEME_COLORS.items():
            if stored.upper() == bg.upper():
                return key
        return "primary"

    @property
    def theme_label(self):
        return ANNOUNCEMENT_THEME_LABELS.get(self.get_theme_key(), "Primary Blue")

    @property
    def display_background_color(self):
        stored = (self.background_color or "").strip()
        if stored in ANNOUNCEMENT_THEME_COLORS:
            return ANNOUNCEMENT_THEME_COLORS[stored][0]
        if stored.startswith("#"):
            return stored
        for bg, _ in ANNOUNCEMENT_THEME_COLORS.values():
            if stored.upper() == bg.upper():
                return bg
        return ANNOUNCEMENT_THEME_COLORS["primary"][0]

    @property
    def display_text_color(self):
        stored = (self.background_color or "").strip()
        if stored in ANNOUNCEMENT_THEME_COLORS:
            return ANNOUNCEMENT_THEME_COLORS[stored][1]
        if (self.text_color or "").startswith("#"):
            return self.text_color
        for bg, txt in ANNOUNCEMENT_THEME_COLORS.values():
            if stored.upper() == bg.upper():
                return txt
        return ANNOUNCEMENT_THEME_COLORS["primary"][1]


class PlatformIntroductionVideo(TimeStampedModel):
    """Single active platform intro video on the landing page."""

    title = models.CharField(max_length=200, default="How Hilaac Academy Works")
    title_somali = models.CharField(max_length=200, default="Sida Loo Isticmaalo Hilaac Academy")
    description = models.TextField(
        blank=True,
        help_text="Optional extended description shown in the admin panel.",
    )
    video_file = models.FileField(
        upload_to="platform_videos/",
        help_text="MP4 or WebM recommended.",
    )
    thumbnail = models.ImageField(
        upload_to="platform_thumbnails/",
        help_text="Cover image shown before play.",
    )
    duration_seconds = models.PositiveIntegerField(
        default=0,
        editable=False,
        help_text="Set automatically when possible; used for completion analytics.",
    )
    is_active = models.BooleanField(default=True)
    impression_count = models.PositiveIntegerField(default=0, editable=False)
    play_count = models.PositiveIntegerField(default=0, editable=False)
    total_watch_seconds = models.PositiveBigIntegerField(default=0, editable=False)
    completion_count = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        verbose_name = "Platform Introduction Video"
        verbose_name_plural = "Platform Introduction Videos"
        ordering = ["-is_active", "-updated_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.is_active:
            PlatformIntroductionVideo.objects.filter(is_active=True).exclude(pk=self.pk).update(
                is_active=False
            )
        super().save(*args, **kwargs)
        if self.thumbnail:
            from apps.core.imaging import IMAGE_PRESETS, optimize_image_field

            optimize_image_field(
                self.thumbnail,
                max_size=IMAGE_PRESETS["course_cover"]["full"],
                preset="course_cover",
            )

    @classmethod
    def get_active(cls):
        return cls.objects.filter(is_active=True).first()

    @property
    def video_url(self):
        if not self.video_file:
            return ""
        try:
            return self.video_file.url
        except ValueError:
            return ""

    @property
    def thumbnail_url(self):
        if not self.thumbnail:
            return ""
        try:
            return self.thumbnail.url
        except ValueError:
            return ""

    @property
    def video_mime_type(self):
        if not self.video_file:
            return "video/mp4"
        ext = self.video_file.name.rsplit(".", 1)[-1].lower()
        return {
            "mp4": "video/mp4",
            "webm": "video/webm",
            "mov": "video/quicktime",
        }.get(ext, "video/mp4")

    @property
    def average_watch_seconds(self):
        if self.play_count == 0:
            return 0
        return self.total_watch_seconds / self.play_count

    @property
    def completion_rate_percent(self):
        if self.play_count == 0:
            return 0.0
        return round((self.completion_count / self.play_count) * 100, 1)

    def record_impression(self):
        PlatformIntroductionVideo.objects.filter(pk=self.pk).update(
            impression_count=models.F("impression_count") + 1
        )

    def record_play(self):
        PlatformIntroductionVideo.objects.filter(pk=self.pk).update(
            play_count=models.F("play_count") + 1
        )

    def record_watch_seconds(self, seconds):
        if seconds <= 0:
            return
        PlatformIntroductionVideo.objects.filter(pk=self.pk).update(
            total_watch_seconds=models.F("total_watch_seconds") + int(seconds)
        )

    def record_completion(self):
        PlatformIntroductionVideo.objects.filter(pk=self.pk).update(
            completion_count=models.F("completion_count") + 1
        )


class LegalPage(TimeStampedModel):
    """Editable legal content for public Privacy Policy and Terms pages."""

    class PageType(models.TextChoices):
        PRIVACY = "privacy", "Privacy Policy"
        TERMS = "terms", "Terms & Conditions"

    page_type = models.CharField(max_length=20, choices=PageType.choices, unique=True)
    title = models.CharField(max_length=200)
    title_so = models.CharField(max_length=200, blank=True, help_text="Somali page title")
    body = models.TextField(
        blank=True,
        help_text="Optional HTML. Leave blank to show the built-in default legal text.",
    )
    body_so = models.TextField(
        blank=True,
        help_text="Optional Somali HTML content.",
    )
    last_updated = models.DateField(auto_now=True)

    class Meta:
        verbose_name = "Legal Page"
        verbose_name_plural = "Legal Pages"
        ordering = ["page_type"]

    def __str__(self):
        return self.title

    @classmethod
    def get_page(cls, page_type: str):
        defaults = {
            cls.PageType.PRIVACY: "Privacy Policy",
            cls.PageType.TERMS: "Terms & Conditions",
        }
        page, _ = cls.objects.get_or_create(
            page_type=page_type,
            defaults={"title": defaults.get(page_type, page_type)},
        )
        return page
