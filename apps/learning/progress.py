"""Student learning progress aggregation for dashboards."""
from django.db.models import Max

from apps.assessments.models import Assignment, AssignmentSubmission, Quiz, QuizAttempt
from apps.assessments.services import course_completion_ready
from apps.certificates.models import Certificate
from apps.courses.models import Enrollment
from apps.learning.models import LessonProgress

from apps.core.dashboard_helpers import compute_learning_streak


def _lessons_progress(student, level):
    total = level.total_lessons
    completed = LessonProgress.objects.filter(
        student=student,
        lesson__module__level=level,
        is_completed=True,
    ).count()
    pct = round((completed / total) * 100) if total else 0
    return {"completed": completed, "total": total, "percent": pct}


def _quiz_progress(student, level):
    quizzes = Quiz.objects.filter(level=level, is_published=True).order_by("is_final", "title")
    rows = []
    passed_count = 0
    for quiz in quizzes:
        best = (
            QuizAttempt.objects.filter(student=student, quiz=quiz)
            .aggregate(best=Max("score"))["best"]
        )
        passed = QuizAttempt.objects.filter(student=student, quiz=quiz, passed=True).exists()
        if passed:
            passed_count += 1
        attempts_used = QuizAttempt.objects.filter(student=student, quiz=quiz).count()
        rows.append(
            {
                "quiz": quiz,
                "best_score": best,
                "passed": passed,
                "attempts_used": attempts_used,
                "attempts_left": max(0, quiz.max_attempts - attempts_used),
            }
        )
    return {"items": rows, "passed": passed_count, "total": quizzes.count()}


def _assignment_progress(student, level):
    assignments = Assignment.objects.filter(module__level=level, is_published=True).order_by(
        "module__order", "title"
    )
    rows = []
    graded_scores = []
    for assignment in assignments:
        sub = AssignmentSubmission.objects.filter(student=student, assignment=assignment).first()
        pct = None
        if sub and sub.grade is not None and assignment.max_score:
            pct = round(float(sub.grade) / assignment.max_score * 100)
            graded_scores.append(pct)
        rows.append({"assignment": assignment, "submission": sub, "score_percent": pct})
    avg = round(sum(graded_scores) / len(graded_scores)) if graded_scores else None
    submitted = sum(1 for r in rows if r["submission"])
    return {
        "items": rows,
        "submitted": submitted,
        "total": assignments.count(),
        "average_score": avg,
    }


def get_course_progress_detail(student, level):
    enrollment = Enrollment.objects.filter(student=student, level=level).first()
    lessons = _lessons_progress(student, level)
    quizzes = _quiz_progress(student, level)
    assignments = _assignment_progress(student, level)
    certificate = Certificate.objects.filter(student=student, level=level).first()
    return {
        "level": level,
        "enrollment": enrollment,
        "lessons": lessons,
        "quizzes": quizzes,
        "assignments": assignments,
        "completion_percent": enrollment.progress_percentage if enrollment else lessons["percent"],
        "certificate_ready": course_completion_ready(student, level),
        "certificate": certificate,
        "has_access": bool(enrollment and enrollment.access_granted),
    }


def get_student_progress_overview(student):
    enrollments = (
        Enrollment.objects.filter(student=student, access_granted=True)
        .exclude(status=Enrollment.Status.CANCELLED)
        .select_related("level", "level__language")
        .order_by("-enrolled_at")
    )
    courses = [get_course_progress_detail(student, e.level) for e in enrollments]
    progresses = [c["completion_percent"] for c in courses]
    return {
        "courses": courses,
        "learning_streak": compute_learning_streak(student),
        "lessons_completed": LessonProgress.objects.filter(student=student, is_completed=True).count(),
        "quizzes_passed": QuizAttempt.objects.filter(student=student, passed=True).count(),
        "certificates_count": Certificate.objects.filter(student=student).count(),
        "avg_progress": round(sum(progresses) / len(progresses)) if progresses else 0,
        "active_courses": enrollments.filter(status=Enrollment.Status.ACTIVE).count(),
    }
