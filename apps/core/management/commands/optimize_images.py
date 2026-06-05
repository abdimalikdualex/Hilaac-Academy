from django.core.management.base import BaseCommand

from apps.courses.models import Lesson, Level
from apps.core.imaging import IMAGE_PRESETS, generate_image_variants, optimize_image_field


class Command(BaseCommand):
    help = "Generate WebP variants and resize existing course/lesson images"

    def handle(self, *args, **options):
        count = 0
        for level in Level.objects.exclude(thumbnail="").exclude(thumbnail__isnull=True):
            optimize_image_field(
                level.thumbnail,
                max_size=IMAGE_PRESETS["course_cover"]["full"],
                preset="course_cover",
            )
            count += 1
            if level.banner:
                optimize_image_field(
                    level.banner,
                    max_size=IMAGE_PRESETS["dashboard_banner"]["full"],
                    preset="dashboard_banner",
                )
                count += 1

        for lesson in Lesson.objects.exclude(thumbnail="").exclude(thumbnail__isnull=True):
            optimize_image_field(
                lesson.thumbnail,
                max_size=IMAGE_PRESETS["thumbnail"]["full"],
                preset="thumbnail",
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f"Optimized {count} image fields."))
