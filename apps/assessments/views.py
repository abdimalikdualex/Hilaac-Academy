from datetime import datetime
from decimal import Decimal

from django.contrib import messages
from apps.core.permissions import student_required
from apps.core.utils import log_audit
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.courses.access import student_has_full_access
from apps.courses.models import Enrollment
from apps.notifications.services import notify_course_completion

from .models import AnswerOption, Question, Quiz, QuizAttempt


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


@student_required
def take_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz.objects.prefetch_related("questions__options"), pk=quiz_id)
    level = quiz.level or quiz.module.level

    if not student_has_full_access(request.user, level):
        messages.error(request, "You must purchase and unlock this course to take quizzes.")
        return redirect("courses:detail", language_slug=level.language.slug, level_slug=level.slug)

    session_key = f"quiz_start_{quiz_id}"
    if session_key not in request.session:
        request.session[session_key] = timezone.now().isoformat()

    if request.method == "POST":
        # Enforce timer server-side
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

        return render(request, "assessments/quiz_result.html", {"quiz": quiz, "attempt": attempt, "level": level})

    return render(request, "assessments/take_quiz.html", {"quiz": quiz, "level": level})
