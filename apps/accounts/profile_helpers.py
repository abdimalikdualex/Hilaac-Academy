"""Profile statistics and context builders for role-based profile pages."""
from django.db.models import Count, Sum

from apps.assessments.models import AssignmentSubmission, QuizAttempt
from apps.certificates.models import Certificate
from apps.courses.models import Enrollment, Lesson, Level
from apps.learning.models import LessonProgress
from apps.payments.currency import revenue_totals
from apps.payments.models import Payment


def profile_stats_for_user(user):
    if user.is_student:
        return _student_stats(user)
    if user.is_instructor:
        return _instructor_stats(user)
    if user.is_super_admin:
        return _admin_stats(user)
    return {}


def _student_stats(user):
    enrollments = Enrollment.objects.filter(student=user)
    active = enrollments.filter(status=Enrollment.Status.ACTIVE).count()
    completed = enrollments.filter(status=Enrollment.Status.COMPLETED).count()
    total = enrollments.exclude(status=Enrollment.Status.CANCELLED).count()
    certificates = Certificate.objects.filter(student=user).count()
    watch_seconds = LessonProgress.objects.filter(student=user).aggregate(
        total=Sum("watched_seconds")
    )["total"] or 0
    return {
        "total_courses": total,
        "active_courses": active,
        "completed_courses": completed,
        "certificates_earned": certificates,
        "study_hours": round(watch_seconds / 3600, 1),
        "lessons_completed": LessonProgress.objects.filter(student=user, is_completed=True).count(),
    }


def _instructor_stats(user):
    levels = Level.objects.filter(instructor=user)
    level_ids = levels.values_list("pk", flat=True)
    revenue = revenue_totals(
        Payment.objects.filter(level__instructor=user, status=Payment.Status.COMPLETED)
    )
    lessons_count = Lesson.objects.filter(module__level__instructor=user).count()
    ratings = [level.average_rating for level in levels if level.average_rating]
    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0
    return {
        "total_courses": levels.count(),
        "total_students": Enrollment.objects.filter(level__instructor=user).values("student").distinct().count(),
        "course_ratings": avg_rating,
        "total_revenue": revenue.get("usd_formatted", "$0"),
        "lessons_uploaded": lessons_count,
        "pending_submissions": AssignmentSubmission.objects.filter(
            assignment__module__level__instructor=user,
            status=AssignmentSubmission.Status.PENDING,
        ).count(),
    }


def _admin_stats(user):
    from apps.accounts.models import User

    return {
        "total_students": User.objects.filter(role=User.Role.STUDENT).count(),
        "total_instructors": User.objects.filter(role=User.Role.INSTRUCTOR).count(),
        "total_courses": Level.objects.filter(is_archived=False).count(),
        "total_certificates": Certificate.objects.filter(is_revoked=False).count(),
        "total_revenue": revenue_totals(
            Payment.objects.filter(status=Payment.Status.COMPLETED)
        ).get("usd_formatted", "$0"),
    }


def security_logs_for_user(user, limit=10):
    from apps.core.models import AuditLog

    return AuditLog.objects.filter(user=user).order_by("-created_at")[:limit]
