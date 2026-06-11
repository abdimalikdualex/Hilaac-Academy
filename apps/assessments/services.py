from django.utils import timezone

from apps.assessments.models import Assignment, AssignmentSubmission, Quiz, QuizAttempt
from apps.learning.models import LessonProgress


def _published_assignments(level):
    return Assignment.objects.filter(module__level=level, is_published=True)


def _published_quizzes(level):
    return Quiz.objects.filter(level=level, is_published=True)


def assignments_submitted_for_level(student, level):
    """All published assignments have a submission (any status except resubmit-only gap)."""
    assignment_ids = _published_assignments(level).values_list("pk", flat=True)
    if not assignment_ids:
        return True
    submitted = AssignmentSubmission.objects.filter(
        student=student,
        assignment_id__in=assignment_ids,
    ).exclude(status=AssignmentSubmission.Status.RESUBMIT)
    return submitted.count() >= len(assignment_ids)


def required_quizzes_passed(student, level):
    quizzes = _published_quizzes(level).filter(is_final=False)
    if not quizzes.exists():
        return True
    for quiz in quizzes:
        if not QuizAttempt.objects.filter(student=student, quiz=quiz, passed=True).exists():
            return False
    return True


def final_quiz_passed(student, level):
    final = Quiz.objects.filter(level=level, is_final=True, is_published=True).first()
    if not final:
        return True
    return QuizAttempt.objects.filter(student=student, quiz=final, passed=True).exists()


def all_lessons_completed(student, level):
    total = level.total_lessons
    if total == 0:
        return False
    completed = LessonProgress.objects.filter(
        student=student,
        lesson__module__level=level,
        is_completed=True,
    ).count()
    return completed >= total


def course_completion_ready(student, level):
    return (
        all_lessons_completed(student, level)
        and assignments_submitted_for_level(student, level)
        and required_quizzes_passed(student, level)
        and final_quiz_passed(student, level)
    )


def submission_status_for_upload(assignment, existing=None):
    from apps.assessments.models import AssignmentSubmission

    now = timezone.now()
    is_late = assignment.due_date and now > assignment.due_date
    if existing and existing.status == AssignmentSubmission.Status.RESUBMIT:
        return AssignmentSubmission.Status.LATE if is_late else AssignmentSubmission.Status.SUBMITTED
    return AssignmentSubmission.Status.LATE if is_late else AssignmentSubmission.Status.SUBMITTED


def student_can_submit(assignment, submission=None):
    if not assignment.is_published:
        return False, "This assignment is not available."
    if submission:
        if submission.status in (
            AssignmentSubmission.Status.GRADED,
            AssignmentSubmission.Status.APPROVED,
        ):
            return False, "This assignment has already been graded."
        if submission.status == AssignmentSubmission.Status.RESUBMIT:
            return True, ""
        if not assignment.allow_resubmit:
            return False, "Resubmission is not allowed for this assignment."
    return True, ""
