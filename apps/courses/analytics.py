"""Per-course analytics shared by admin and instructor portals."""
from django.db.models import Sum

from apps.courses.models import Enrollment


def course_analytics(level):
    """Return a dict of analytics for a single course (Level)."""
    enrollments = list(level.enrollments.select_related("student"))
    student_count = len(enrollments)
    completed = sum(1 for e in enrollments if e.status == Enrollment.Status.COMPLETED)

    progresses = [e.progress_percentage for e in enrollments]
    avg_progress = round(sum(progresses) / len(progresses)) if progresses else 0
    completion_rate = round((completed / student_count) * 100) if student_count else 0

    try:
        from apps.payments.models import Payment

        revenue = (
            Payment.objects.filter(level=level, status=Payment.Status.COMPLETED).aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )
    except Exception:
        revenue = 0

    from apps.learning.models import LessonProgress

    lessons_completed = LessonProgress.objects.filter(
        lesson__module__level=level, is_completed=True
    ).count()

    return {
        "student_count": student_count,
        "completed": completed,
        "avg_progress": avg_progress,
        "completion_rate": completion_rate,
        "revenue": revenue,
        "lessons_completed": lessons_completed,
    }
