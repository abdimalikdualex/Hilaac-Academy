from django.db import models

from apps.core.models import TimeStampedModel


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
