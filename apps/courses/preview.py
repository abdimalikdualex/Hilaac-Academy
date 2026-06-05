"""Free preview lesson rules for Hilaac Academy courses."""
from django.core.exceptions import ValidationError

from .models import Lesson

# MVP: only the first lesson may be free preview (increase to 3 later if needed).
MAX_PREVIEW_LESSONS = 1


def get_ordered_lessons(level):
    return Lesson.objects.filter(module__level=level, is_published=True).order_by(
        "module__order", "order", "id"
    )


def get_first_lesson(level):
    return get_ordered_lessons(level).first()


def get_first_preview_lesson(level):
    return get_ordered_lessons(level).filter(is_preview=True).first()


def _is_first_lesson(lesson, level):
    first = get_first_lesson(level)
    if not first:
        return True
    if lesson.pk and lesson.pk == first.pk:
        return True
    if not lesson.module_id:
        return False
    lesson_key = (lesson.module.order, lesson.order)
    first_key = (first.module.order, first.order)
    if lesson.pk:
        return lesson_key == first_key
    return lesson_key < first_key


def validate_preview_lesson(lesson, *, is_preview=None):
    """Raise ValidationError if preview rules would be violated."""
    flag = lesson.is_preview if is_preview is None else is_preview
    if not flag:
        return

    level = lesson.module.level
    if not _is_first_lesson(lesson, level):
        raise ValidationError(
            "Only the first lesson in the course can be marked as a free preview."
        )

    existing = get_ordered_lessons(level).filter(is_preview=True)
    if lesson.pk:
        existing = existing.exclude(pk=lesson.pk)
    if existing.count() >= MAX_PREVIEW_LESSONS:
        raise ValidationError(
            f"Maximum {MAX_PREVIEW_LESSONS} free preview lesson per course."
        )


def enforce_single_preview(level):
    """Ensure only the first published lesson is marked preview."""
    lessons = list(get_ordered_lessons(level))
    Lesson.objects.filter(module__level=level).update(is_preview=False)
    if lessons:
        first = lessons[0]
        Lesson.objects.filter(pk=first.pk).update(is_preview=True)


def get_enroll_or_checkout_url(level, user):
    """URL for locked-lesson / purchase CTAs."""
    from django.urls import reverse

    detail = level.get_absolute_url()
    if level.is_free:
        if user.is_authenticated and getattr(user, "is_student", False):
            return reverse("courses:enroll", kwargs={"level_id": level.id})
        return f"{reverse('accounts:login')}?next={detail}"
    if user.is_authenticated and getattr(user, "is_student", False):
        return reverse("payments:checkout", kwargs={"level_id": level.id})
    return f"{reverse('accounts:login')}?next={detail}"
