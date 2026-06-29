"""Certificate eligibility breakdown for student UI."""
from apps.assessments.models import Assignment, AssignmentSubmission, Quiz, QuizAttempt
from apps.assessments.services import (
    all_lessons_completed,
    assignments_submitted_for_level,
    final_quiz_passed,
    required_quizzes_passed,
)
from apps.certificates.models import Certificate
from apps.courses.models import Enrollment
from apps.learning.models import LessonProgress


def certificate_requirements(student, level):
    total_lessons = level.total_lessons
    completed_lessons = LessonProgress.objects.filter(
        student=student,
        lesson__module__level=level,
        is_completed=True,
    ).count()

    published_assignments = Assignment.objects.filter(module__level=level, is_published=True)
    assignment_total = published_assignments.count()
    assignment_done = AssignmentSubmission.objects.filter(
        student=student,
        assignment__in=published_assignments,
    ).exclude(status=AssignmentSubmission.Status.RESUBMIT).count()

    module_quizzes = Quiz.objects.filter(level=level, is_published=True, is_final=False)
    quiz_total = module_quizzes.count()
    quiz_passed = sum(
        1
        for q in module_quizzes
        if QuizAttempt.objects.filter(student=student, quiz=q, passed=True).exists()
    )

    final = Quiz.objects.filter(level=level, is_published=True, is_final=True).first()
    final_passed = not final or QuizAttempt.objects.filter(
        student=student, quiz=final, passed=True
    ).exists()

    cert = Certificate.objects.filter(student=student, level=level).first()
    enrollment = Enrollment.objects.filter(student=student, level=level).first()

    checks = [
        {
            "key": "lessons",
            "label": "Complete all lessons",
            "done": all_lessons_completed(student, level),
            "detail": f"{completed_lessons}/{total_lessons} lessons",
        },
        {
            "key": "assignments",
            "label": "Submit all assignments",
            "done": assignments_submitted_for_level(student, level),
            "detail": f"{assignment_done}/{assignment_total} submitted",
        },
        {
            "key": "quizzes",
            "label": "Pass required quizzes",
            "done": required_quizzes_passed(student, level),
            "detail": f"{quiz_passed}/{quiz_total} passed",
        },
        {
            "key": "final",
            "label": "Pass final exam",
            "done": final_passed,
            "detail": "Final exam passed" if final_passed else ("No final exam" if not final else "Not passed yet"),
        },
    ]

    ready = all(c["done"] for c in checks) and total_lessons > 0
    return {
        "checks": checks,
        "ready": ready,
        "certificate": cert,
        "enrollment": enrollment,
        "percent_complete": round(sum(1 for c in checks if c["done"]) / len(checks) * 100) if checks else 0,
    }


def in_progress_certificate_courses(student):
    """Enrolled courses without a certificate yet — show requirements."""
    enrolled_ids = (
        Enrollment.objects.filter(student=student, access_granted=True)
        .exclude(status=Enrollment.Status.CANCELLED)
        .values_list("level_id", flat=True)
    )
    issued_ids = Certificate.objects.filter(student=student).values_list("level_id", flat=True)
    from apps.courses.models import Level

    levels = Level.objects.filter(pk__in=enrolled_ids).exclude(pk__in=issued_ids).select_related("language")
    return [{"level": level, "requirements": certificate_requirements(student, level)} for level in levels]
