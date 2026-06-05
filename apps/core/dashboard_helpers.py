"""Shared dashboard context helpers."""
from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.assessments.models import Assignment, AssignmentSubmission, Quiz, QuizAttempt
from apps.certificates.models import Certificate
from apps.courses.models import Enrollment, Level
from apps.learning.models import LessonProgress
from apps.notifications.models import Notification
from apps.payments.currency import revenue_totals
from apps.payments.models import Payment


def compute_learning_streak(student):
    dates = set(
        LessonProgress.objects.filter(student=student, last_watched_at__isnull=False)
        .values_list("last_watched_at__date", flat=True)
    )
    if not dates:
        return 0
    streak = 0
    day = timezone.localdate()
    if day not in dates and (day - timedelta(days=1)) not in dates:
        return 0
    if day not in dates:
        day -= timedelta(days=1)
    while day in dates:
        streak += 1
        day -= timedelta(days=1)
    return streak


def student_dashboard_context(user):
    enrollments = Enrollment.objects.filter(student=user).select_related("level", "level__language")
    active = enrollments.filter(status=Enrollment.Status.ACTIVE)
    completed = enrollments.filter(status=Enrollment.Status.COMPLETED)
    progress_qs = LessonProgress.objects.filter(student=user, is_completed=True)
    quiz_attempts = QuizAttempt.objects.filter(student=user).select_related("quiz").order_by("-completed_at")[:10]
    assessments_passed = QuizAttempt.objects.filter(student=user, passed=True).count()
    certificates = Certificate.objects.filter(student=user)

    activities = []
    for e in enrollments.order_by("-enrolled_at")[:5]:
        activities.append({"type": "enrollment", "text": f"Enrolled in {e.level.name}", "date": e.enrolled_at})
    for p in LessonProgress.objects.filter(student=user, is_completed=True).order_by("-last_watched_at")[:5]:
        activities.append({"type": "lesson", "text": f"Completed {p.lesson.title}", "date": p.last_watched_at})
    for a in quiz_attempts[:5]:
        if a.completed_at:
            activities.append({"type": "quiz", "text": f"Scored {a.score}% on {a.quiz.title}", "date": a.completed_at})
    for c in certificates.order_by("-issued_at")[:3]:
        activities.append({"type": "certificate", "text": f"Earned certificate for {c.level.name}", "date": c.issued_at})
    activities.sort(key=lambda x: x["date"], reverse=True)

    total_watch_seconds = LessonProgress.objects.filter(student=user).values_list("watched_seconds", flat=True)
    active_list = list(active)
    progresses = [e.progress_percentage for e in active_list]
    avg_progress = round(sum(progresses) / len(progresses)) if progresses else 0

    purchase_totals = revenue_totals(
        Payment.objects.filter(student=user, status=Payment.Status.COMPLETED)
    )

    return {
        "purchase_totals": purchase_totals,
        "active_enrollments": active_list,
        "completed_enrollments": completed,
        "pending_payments": Payment.objects.filter(
            student=user, status=Payment.Status.PENDING
        ).exclude(level_id__in=enrollments.values_list("level_id", flat=True)).select_related("level")[:5],
        "lessons_completed": progress_qs.count(),
        "assessments_passed": assessments_passed,
        "certificates_count": certificates.count(),
        "hours_studied": round(sum(total_watch_seconds) / 3600, 1),
        "learning_streak": compute_learning_streak(user),
        "avg_course_progress": round(avg_progress),
        "recent_notifications": Notification.objects.filter(user=user)[:5],
        "certificates": certificates[:3],
        "quiz_attempts": quiz_attempts,
        "recent_activity": activities[:10],
    }


def instructor_dashboard_context(instructor):
    levels = Level.objects.filter(instructor=instructor).annotate(
        student_count=Count("enrollments", distinct=True)
    ).select_related("language")
    level_ids = levels.values_list("pk", flat=True)

    total_students = (
        Enrollment.objects.filter(level__instructor=instructor).values("student").distinct().count()
    )
    pending_submissions = AssignmentSubmission.objects.filter(
        assignment__module__level__instructor=instructor,
        status=AssignmentSubmission.Status.PENDING,
    ).select_related("student", "assignment", "assignment__module__level")[:10]

    lesson_views = LessonProgress.objects.filter(lesson__module__level__instructor=instructor).count()
    completed_enrollments = Enrollment.objects.filter(
        level__instructor=instructor, status=Enrollment.Status.COMPLETED
    ).count()
    total_enrollments = Enrollment.objects.filter(level__instructor=instructor).count()
    completion_rate = round((completed_enrollments / total_enrollments) * 100) if total_enrollments else 0

    recent_enrollments = (
        Enrollment.objects.filter(level__instructor=instructor)
        .select_related("student", "level")
        .order_by("-enrolled_at")[:8]
    )

    return {
        "levels": levels,
        "total_courses": levels.count(),
        "total_students": total_students,
        "pending_submissions": pending_submissions,
        "pending_submission_count": AssignmentSubmission.objects.filter(
            assignment__module__level__instructor=instructor,
            status=AssignmentSubmission.Status.PENDING,
        ).count(),
        "lesson_views": lesson_views,
        "completion_rate": completion_rate,
        "recent_enrollments": recent_enrollments,
        "recent_notifications": Notification.objects.filter(user=instructor)[:5],
    }
