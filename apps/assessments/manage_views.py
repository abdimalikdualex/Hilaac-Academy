"""Instructor assignment and quiz management."""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.core.permissions import instructor_required
from apps.core.utils import log_audit
from apps.courses.models import Module

from .forms import AssignmentForm, AssignmentGradeForm, QuizForm
from .models import Assignment, AssignmentSubmission, Quiz


def _own_module(request, module_id):
    return get_object_or_404(
        Module.objects.select_related("level"),
        pk=module_id,
        level__instructor=request.user,
    )


def _own_assignment(request, pk):
    return get_object_or_404(
        Assignment.objects.select_related("module__level"),
        pk=pk,
        module__level__instructor=request.user,
    )


def _own_quiz(request, pk):
    quiz = get_object_or_404(Quiz.objects.select_related("module__level", "level"), pk=pk)
    level = quiz.level or quiz.module.level
    if level.instructor_id != request.user.id:
        from django.http import Http404

        raise Http404
    return quiz


@instructor_required
def instructor_assignment_add(request, module_id):
    module = _own_module(request, module_id)
    if request.method == "POST":
        form = AssignmentForm(request.POST, request.FILES)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.module = module
            assignment.save()
            log_audit(request, "assignment_create", "Assignment", assignment.pk, assignment.title)
            messages.success(request, "Assignment created.")
            return redirect("instructor:level", level_id=module.level_id)
    else:
        form = AssignmentForm()
    return render(
        request,
        "instructor/assignment_form.html",
        {"form": form, "title": "Create Assignment", "module": module, "level": module.level},
    )


@instructor_required
def instructor_assignment_edit(request, pk):
    assignment = _own_assignment(request, pk)
    if request.method == "POST":
        form = AssignmentForm(request.POST, request.FILES, instance=assignment)
        if form.is_valid():
            form.save()
            log_audit(request, "assignment_update", "Assignment", assignment.pk, assignment.title)
            messages.success(request, "Assignment updated.")
            return redirect("instructor:level", level_id=assignment.module.level_id)
    else:
        form = AssignmentForm(instance=assignment)
    return render(
        request,
        "instructor/assignment_form.html",
        {
            "form": form,
            "title": "Edit Assignment",
            "assignment": assignment,
            "module": assignment.module,
            "level": assignment.module.level,
        },
    )


@instructor_required
def instructor_assignment_delete(request, pk):
    assignment = _own_assignment(request, pk)
    level_id = assignment.module.level_id
    if request.method == "POST":
        title = assignment.title
        assignment.delete()
        log_audit(request, "assignment_delete", "Assignment", pk, title)
        messages.success(request, "Assignment deleted.")
        return redirect("instructor:level", level_id=level_id)
    return render(
        request,
        "partials/confirm_delete.html",
        {
            "object_name": "Assignment",
            "object_label": assignment.title,
            "cancel_url": reverse("instructor:level", kwargs={"level_id": level_id}),
        },
    )


@instructor_required
def instructor_assignment_toggle_publish(request, pk):
    assignment = _own_assignment(request, pk)
    assignment.is_published = not assignment.is_published
    assignment.save(update_fields=["is_published"])
    state = "published" if assignment.is_published else "unpublished"
    messages.success(request, f"Assignment {state}.")
    return redirect("instructor:level", level_id=assignment.module.level_id)


@instructor_required
def instructor_assignment_extend_due(request, pk):
    assignment = _own_assignment(request, pk)
    if request.method == "POST":
        new_due = request.POST.get("due_date")
        if new_due:
            from django.utils.dateparse import parse_datetime

            parsed = parse_datetime(new_due)
            if parsed:
                assignment.due_date = parsed
                assignment.save(update_fields=["due_date"])
                log_audit(request, "assignment_extend_due", "Assignment", assignment.pk)
                messages.success(request, "Due date extended.")
        return redirect("instructor:assignment_edit", pk=pk)
    return render(request, "instructor/assignment_extend_due.html", {"assignment": assignment})


@instructor_required
def instructor_quiz_add(request, module_id):
    module = _own_module(request, module_id)
    if request.method == "POST":
        form = QuizForm(request.POST)
        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.module = module
            quiz.save()
            log_audit(request, "quiz_create", "Quiz", quiz.pk, quiz.title)
            messages.success(request, "Quiz created. Add questions in Django admin for now.")
            return redirect("instructor:level", level_id=module.level_id)
    else:
        form = QuizForm()
    return render(
        request,
        "instructor/quiz_form.html",
        {"form": form, "title": "Create Quiz", "module": module, "level": module.level},
    )


@instructor_required
def instructor_quiz_edit(request, pk):
    quiz = _own_quiz(request, pk)
    if request.method == "POST":
        form = QuizForm(request.POST, instance=quiz)
        if form.is_valid():
            form.save()
            log_audit(request, "quiz_update", "Quiz", quiz.pk, quiz.title)
            messages.success(request, "Quiz updated.")
            level = quiz.level or quiz.module.level
            return redirect("instructor:level", level_id=level.id)
    else:
        form = QuizForm(instance=quiz)
    level = quiz.level or quiz.module.level
    return render(
        request,
        "instructor/quiz_form.html",
        {"form": form, "title": "Edit Quiz", "quiz": quiz, "level": level},
    )


@instructor_required
def instructor_quiz_delete(request, pk):
    quiz = _own_quiz(request, pk)
    level = quiz.level or quiz.module.level
    if request.method == "POST":
        title = quiz.title
        quiz.delete()
        log_audit(request, "quiz_delete", "Quiz", pk, title)
        messages.success(request, "Quiz deleted.")
        return redirect("instructor:level", level_id=level.id)
    return render(
        request,
        "partials/confirm_delete.html",
        {
            "object_name": "Quiz",
            "object_label": quiz.title,
            "cancel_url": reverse("instructor:level", kwargs={"level_id": level.id}),
        },
    )


@instructor_required
def instructor_quiz_toggle_publish(request, pk):
    quiz = _own_quiz(request, pk)
    quiz.is_published = not quiz.is_published
    quiz.save(update_fields=["is_published"])
    level = quiz.level or quiz.module.level
    messages.success(request, f"Quiz {'published' if quiz.is_published else 'unpublished'}.")
    return redirect("instructor:level", level_id=level.id)


def grade_submission_context(submission, form):
    return {
        "submission": submission,
        "form": form,
        "max_score": submission.assignment.max_score,
    }
