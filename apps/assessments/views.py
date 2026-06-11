from datetime import datetime
from decimal import Decimal

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.core.permissions import student_required
from apps.core.utils import log_audit
from apps.courses.access import student_has_full_access
from apps.courses.models import Enrollment

from .forms import AssignmentSubmissionForm
from .models import AnswerOption, Assignment, AssignmentSubmission, Question, Quiz, QuizAttempt
from .services import student_can_submit, submission_status_for_upload


def _grade_quiz(quiz, answers):
    questions = quiz.questions.all()
    total_points = sum(q.points for q in questions) or 1
    earned = Decimal("0")

    for question in questions:
        answer = answers.get(str(question.id), "").strip()
        if question.question_type == Question.QuestionType.FILL_BLANK:
            if answer.lower() == question.correct_answer.lower():
                earned += question.points
        elif question.question_type in (
            Question.QuestionType.MULTIPLE_CHOICE,
            Question.QuestionType.TRUE_FALSE,
            Question.QuestionType.READING,
            Question.QuestionType.LISTENING,
        ):
            try:
                option = AnswerOption.objects.get(pk=int(answer), question=question)
                if option.is_correct:
                    earned += question.points
            except (ValueError, AnswerOption.DoesNotExist):
                pass

    score = (earned / total_points) * 100
    return round(score, 2)


def _quiz_level(quiz):
    return quiz.level or quiz.module.level


@student_required
def take_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz.objects.prefetch_related("questions__options"), pk=quiz_id)
    level = _quiz_level(quiz)

    if not quiz.is_published:
        messages.error(request, "This quiz is not available yet.")
        return redirect("learning:course_view", level_id=level.id)

    if not student_has_full_access(request.user, level):
        messages.error(request, "You must purchase and unlock this course to take quizzes.")
        return redirect("courses:detail", language_slug=level.language.slug, level_slug=level.slug)

    attempts_count = QuizAttempt.objects.filter(student=request.user, quiz=quiz).count()
    if attempts_count >= quiz.max_attempts:
        messages.error(request, f"You have used all {quiz.max_attempts} attempts for this quiz.")
        return redirect("learning:course_view", level_id=level.id)

    session_key = f"quiz_start_{quiz_id}"
    if session_key not in request.session:
        request.session[session_key] = timezone.now().isoformat()

    if request.method == "POST":
        if quiz.time_limit_minutes:
            started = datetime.fromisoformat(request.session.get(session_key))
            if timezone.is_naive(started):
                started = timezone.make_aware(started)
            elapsed = (timezone.now() - started).total_seconds() / 60
            if elapsed > quiz.time_limit_minutes + 1:
                messages.error(request, "Time is up! Please retake the quiz.")
                del request.session[session_key]
                return redirect("assessments:take_quiz", quiz_id=quiz.id)

        answers = {}
        for question in quiz.questions.all():
            key = f"question_{question.id}"
            answers[str(question.id)] = request.POST.get(key, "")
        score = _grade_quiz(quiz, answers)
        passed = score >= quiz.pass_mark
        attempt = QuizAttempt.objects.create(
            student=request.user,
            quiz=quiz,
            score=score,
            passed=passed,
            completed_at=timezone.now(),
        )
        del request.session[session_key]

        if quiz.is_final and passed:
            from apps.certificates.services import maybe_issue_certificate

            cert = maybe_issue_certificate(request.user, level)
            if cert:
                log_audit(request, "certificate_issue", "Certificate", cert.pk, cert.certificate_id)

        return render(
            request,
            "assessments/quiz_result.html",
            {"quiz": quiz, "attempt": attempt, "level": level, "show_answers": quiz.show_correct_answers},
        )

    return render(
        request,
        "assessments/take_quiz.html",
        {"quiz": quiz, "level": level, "attempts_remaining": quiz.max_attempts - attempts_count},
    )


@student_required
def assignment_detail(request, assignment_id):
    assignment = get_object_or_404(
        Assignment.objects.select_related("module__level__language"),
        pk=assignment_id,
        is_published=True,
    )
    level = assignment.module.level
    if not Enrollment.objects.filter(student=request.user, level=level).exclude(
        status=Enrollment.Status.CANCELLED
    ).exists():
        messages.error(request, "You are not enrolled in this course.")
        return redirect("student:assignments")

    submission = AssignmentSubmission.objects.filter(student=request.user, assignment=assignment).first()
    can_submit, reason = student_can_submit(assignment, submission)
    return render(
        request,
        "assessments/assignment_detail.html",
        {
            "assignment": assignment,
            "level": level,
            "submission": submission,
            "can_submit": can_submit,
            "submit_reason": reason,
        },
    )


@student_required
def assignment_submit(request, assignment_id):
    assignment = get_object_or_404(
        Assignment.objects.select_related("module__level"),
        pk=assignment_id,
        is_published=True,
    )
    level = assignment.module.level
    if not Enrollment.objects.filter(student=request.user, level=level).exclude(
        status=Enrollment.Status.CANCELLED
    ).exists():
        messages.error(request, "You are not enrolled in this course.")
        return redirect("student:assignments")

    submission = AssignmentSubmission.objects.filter(student=request.user, assignment=assignment).first()
    can_submit, reason = student_can_submit(assignment, submission)
    if not can_submit:
        messages.error(request, reason)
        return redirect("assessments:assignment_detail", assignment_id=assignment.id)

    if request.method == "POST":
        form = AssignmentSubmissionForm(request.POST, request.FILES, instance=submission)
        if form.is_valid():
            sub = form.save(commit=False)
            sub.student = request.user
            sub.assignment = assignment
            sub.status = submission_status_for_upload(assignment, submission)
            sub.save()
            log_audit(request, "assignment_submit", "AssignmentSubmission", sub.pk, assignment.title)
            from apps.notifications.services import notify_assignment_submitted

            instructor = assignment.module.level.instructor
            if instructor:
                notify_assignment_submitted(instructor, sub)
            messages.success(request, "Assignment submitted successfully.")
            return redirect("assessments:assignment_detail", assignment_id=assignment.id)
    else:
        form = AssignmentSubmissionForm(instance=submission)

    return render(
        request,
        "assessments/assignment_submit.html",
        {"assignment": assignment, "form": form, "submission": submission},
    )
