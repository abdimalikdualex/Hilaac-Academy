from django.contrib import messages
from django.contrib.auth.views import PasswordChangeView
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from decimal import Decimal

from apps.accounts.forms import HilaacPasswordChangeForm
from apps.assessments.models import AssignmentSubmission, Quiz
from apps.core.dashboard_helpers import instructor_dashboard_context
from apps.core.utils import log_audit
from apps.courses.analytics import course_analytics
from apps.courses.forms import CourseForm, LessonForm, ModuleForm
from apps.courses.models import Enrollment, Lesson, Level, Module
from apps.notifications.models import Notification

from apps.core.permissions import (
    instructor_owns_submission,
    instructor_required,
)


def _own_level(request, level_id):
    return get_object_or_404(Level, pk=level_id, instructor=request.user)


def _own_module(request, module_id):
    return get_object_or_404(Module, pk=module_id, level__instructor=request.user)


def _own_lesson(request, lesson_id):
    return get_object_or_404(
        Lesson.objects.select_related("module__level"),
        pk=lesson_id,
        module__level__instructor=request.user,
    )


def _move(obj, queryset, direction):
    """Swap the order value of obj with its neighbour (up/down)."""
    items = list(queryset)
    idx = next((i for i, o in enumerate(items) if o.pk == obj.pk), None)
    if idx is None:
        return
    swap = idx - 1 if direction == "up" else idx + 1
    if 0 <= swap < len(items):
        other = items[swap]
        obj.order, other.order = other.order, obj.order
        obj.save(update_fields=["order"])
        other.save(update_fields=["order"])


@instructor_required
def instructor_dashboard(request):
    return render(request, "instructor/dashboard.html", instructor_dashboard_context(request.user))


@instructor_required
def instructor_courses(request):
    levels = Level.objects.filter(instructor=request.user).annotate(
        student_count=Count("enrollments")
    ).select_related("language")
    return render(request, "instructor/courses.html", {"levels": levels})


@instructor_required
def instructor_analytics(request):
    levels = Level.objects.filter(instructor=request.user).select_related("language")
    stats = [{"level": level, "analytics": course_analytics(level)} for level in levels]
    ctx = instructor_dashboard_context(request.user)
    ctx["course_stats"] = stats
    return render(request, "instructor/analytics.html", ctx)


@instructor_required
def instructor_quizzes(request):
    from django.db.models import Q

    quizzes = (
        Quiz.objects.filter(Q(level__instructor=request.user) | Q(module__level__instructor=request.user))
        .distinct()
        .select_related("level", "module")
    )
    return render(request, "instructor/quizzes.html", {"quizzes": quizzes})


@instructor_required
def instructor_students_all(request):
    enrollments = (
        Enrollment.objects.filter(level__instructor=request.user)
        .select_related("student", "level", "level__language")
        .order_by("-enrolled_at")
    )
    return render(request, "instructor/students_all.html", {"enrollments": enrollments})


@instructor_required
def instructor_notifications(request):
    notes = Notification.objects.filter(user=request.user)
    return render(request, "instructor/notifications.html", {"notifications": notes})


@instructor_required
def instructor_profile(request):
    from django.http import HttpResponseRedirect, HttpResponsePermanentRedirect

    from apps.accounts.profile_views import handle_profile_update

    result = handle_profile_update(request, "instructor:profile")
    if isinstance(result, (HttpResponseRedirect, HttpResponsePermanentRedirect)):
        return result
    return render(request, "instructor/profile.html", result)


@instructor_required
def instructor_settings(request):
    from apps.accounts.forms import AccountSettingsForm, NotificationPreferencesForm
    from apps.accounts.profile_helpers import profile_stats_for_user

    user = request.user
    account_form = AccountSettingsForm(instance=user)
    notification_form = NotificationPreferencesForm(instance=user)

    if request.method == "POST":
        form_type = request.POST.get("form_type")
        if form_type == "notifications":
            notification_form = NotificationPreferencesForm(request.POST, instance=user)
            if notification_form.is_valid():
                notification_form.save()
                log_audit(request, "profile_notifications_update", "User", user.pk)
                messages.success(request, "Notification preferences saved.")
                return redirect("instructor:settings")
        elif form_type == "account":
            account_form = AccountSettingsForm(request.POST, instance=user)
            if account_form.is_valid():
                old_email = user.email
                account_form.save()
                if old_email != user.email:
                    log_audit(request, "profile_email_change", "User", user.pk, f"{old_email} -> {user.email}")
                else:
                    log_audit(request, "profile_account_update", "User", user.pk)
                messages.success(request, "Account settings saved.")
                return redirect("instructor:settings")

    return render(
        request,
        "instructor/settings.html",
        {
            "account_form": account_form,
            "notification_form": notification_form,
            "password_form": HilaacPasswordChangeForm(user=user),
            "profile_stats": profile_stats_for_user(user),
        },
    )


class InstructorPasswordChangeView(PasswordChangeView):
    form_class = HilaacPasswordChangeForm
    template_name = "instructor/password_change.html"
    success_url = reverse_lazy("instructor:settings")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_instructor:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        from apps.core.utils import log_audit

        log_audit(self.request, "profile_password_change", "User", self.request.user.pk)
        messages.success(self.request, "Password changed successfully.")
        return super().form_valid(form)


# --- Course CRUD (own courses) ---
@instructor_required
def instructor_course_add(request):
    if request.method == "POST":
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            level = form.save(commit=False)
            level.instructor = request.user
            level.is_published = False  # start as draft
            level.save()
            messages.success(request, f"Course '{level.name}' created as a draft. Add modules and lessons next.")
            return redirect("instructor:level", level_id=level.id)
    else:
        form = CourseForm()
    return render(request, "instructor/course_form.html", {"form": form, "title": "Create Course", "builder_step": 1})


@instructor_required
def instructor_course_edit(request, level_id):
    level = _own_level(request, level_id)
    if request.method == "POST":
        form = CourseForm(request.POST, request.FILES, instance=level)
        if form.is_valid():
            form.save()
            messages.success(request, "Course updated.")
            return redirect("instructor:level", level_id=level.id)
    else:
        form = CourseForm(instance=level)
    return render(request, "instructor/course_form.html", {"form": form, "title": "Edit Course", "level": level})


@instructor_required
def instructor_course_publish(request, level_id):
    level = _own_level(request, level_id)
    if level.is_archived:
        messages.error(request, "Restore the course before publishing.")
        return redirect("instructor:level", level_id=level.id)
    level.is_published = not level.is_published
    level.save(update_fields=["is_published"])
    messages.success(request, f"Course {'published' if level.is_published else 'unpublished'}.")
    return redirect("instructor:level", level_id=level.id)


@instructor_required
def instructor_course_archive(request, level_id):
    level = _own_level(request, level_id)
    level.is_archived = not level.is_archived
    if level.is_archived:
        level.is_published = False
    level.save(update_fields=["is_archived", "is_published"])
    messages.success(request, f"Course {'archived' if level.is_archived else 'restored'}.")
    return redirect("instructor:dashboard")


@instructor_required
def instructor_level(request, level_id):
    level = get_object_or_404(
        Level.objects.select_related("language").prefetch_related("modules__lessons"),
        pk=level_id,
        instructor=request.user,
    )
    from apps.courses.preview import get_first_lesson

    return render(
        request,
        "instructor/level_detail.html",
        {
            "level": level,
            "analytics": course_analytics(level),
            "first_lesson": get_first_lesson(level),
            "builder_step": 2,
        },
    )


# --- Modules ---
@instructor_required
def instructor_module_add(request, level_id):
    level = _own_level(request, level_id)
    if request.method == "POST":
        form = ModuleForm(request.POST)
        if form.is_valid():
            module = form.save(commit=False)
            module.level = level
            module.save()
            messages.success(request, "Module added.")
            return redirect("instructor:level", level_id=level.id)
    else:
        form = ModuleForm(initial={"level": level, "order": level.modules.count() + 1})
    form.fields["level"].queryset = Level.objects.filter(pk=level.pk)
    return render(request, "instructor/module_form.html", {"form": form, "level": level, "builder_step": 2})


@instructor_required
def instructor_module_edit(request, module_id):
    module = _own_module(request, module_id)
    if request.method == "POST":
        form = ModuleForm(request.POST, instance=module)
        if form.is_valid():
            form.save()
            messages.success(request, "Module updated.")
            return redirect("instructor:level", level_id=module.level.id)
    else:
        form = ModuleForm(instance=module)
    form.fields["level"].queryset = Level.objects.filter(pk=module.level.pk)
    return render(request, "instructor/module_form.html", {"form": form, "level": module.level, "module": module, "builder_step": 2})


@instructor_required
def instructor_module_delete(request, module_id):
    module = _own_module(request, module_id)
    level_id = module.level.id
    if request.method == "POST":
        module.delete()
        messages.success(request, "Module deleted.")
        return redirect("instructor:level", level_id=level_id)
    return render(request, "instructor/module_confirm_delete.html", {"module": module, "level": module.level})


@instructor_required
def instructor_module_move(request, module_id, direction):
    module = _own_module(request, module_id)
    _move(module, module.level.modules.order_by("order", "id"), direction)
    return redirect("instructor:level", level_id=module.level.id)


# --- Lessons ---
@instructor_required
def instructor_lesson_add(request, module_id):
    module = _own_module(request, module_id)
    if request.method == "POST":
        form = LessonForm(request.POST, request.FILES)
        if form.is_valid():
            lesson = form.save()
            from apps.courses.preview import enforce_single_preview

            enforce_single_preview(module.level)
            messages.success(request, f"Lesson '{lesson.title}' uploaded.")
            return redirect("instructor:level", level_id=module.level.id)
    else:
        form = LessonForm(
            initial={"module": module, "order": module.lessons.count() + 1, "lesson_type": Lesson.LessonType.VIDEO}
        )
    form.fields["module"].queryset = Module.objects.filter(level__instructor=request.user)
    return render(request, "instructor/lesson_form.html", {"form": form, "module": module, "level": module.level, "builder_step": 3})


@instructor_required
def instructor_lesson_edit(request, lesson_id):
    lesson = _own_lesson(request, lesson_id)
    if request.method == "POST":
        form = LessonForm(request.POST, request.FILES, instance=lesson)
        if form.is_valid():
            form.save()
            from apps.courses.preview import enforce_single_preview

            enforce_single_preview(lesson.module.level)
            messages.success(request, "Lesson updated.")
            return redirect("instructor:level", level_id=lesson.module.level.id)
    else:
        form = LessonForm(instance=lesson)
    form.fields["module"].queryset = Module.objects.filter(level__instructor=request.user)
    return render(
        request,
        "instructor/lesson_form.html",
        {"form": form, "module": lesson.module, "level": lesson.module.level, "lesson": lesson, "builder_step": 3},
    )


@instructor_required
def instructor_lesson_preview(request, lesson_id):
    lesson = _own_lesson(request, lesson_id)
    return render(request, "courses/lesson_preview.html", {"lesson": lesson, "level": lesson.module.level, "instructor_view": True})


@instructor_required
def instructor_lesson_delete(request, lesson_id):
    lesson = _own_lesson(request, lesson_id)
    level_id = lesson.module.level.id
    if request.method == "POST":
        title = lesson.title
        level = lesson.module.level
        lesson.delete()
        from apps.courses.preview import enforce_single_preview

        enforce_single_preview(level)
        messages.success(request, f"Lesson '{title}' deleted.")
        return redirect("instructor:level", level_id=level_id)
    return render(request, "courses/lesson_confirm_delete.html", {"lesson": lesson, "level": lesson.module.level, "instructor_view": True})


@instructor_required
def instructor_lesson_move(request, lesson_id, direction):
    lesson = _own_lesson(request, lesson_id)
    _move(lesson, lesson.module.lessons.order_by("order", "id"), direction)
    return redirect("instructor:level", level_id=lesson.module.level.id)


# --- Students / progress (own courses only) ---
@instructor_required
def instructor_students(request, level_id):
    level = _own_level(request, level_id)
    enrollments = level.enrollments.select_related("student").order_by("-enrolled_at")
    return render(
        request,
        "instructor/students.html",
        {"level": level, "enrollments": enrollments, "analytics": course_analytics(level)},
    )


# --- Assignments (own courses only) ---
@instructor_required
def instructor_assignments(request):
    submissions = AssignmentSubmission.objects.filter(
        assignment__module__level__instructor=request.user,
        status=AssignmentSubmission.Status.PENDING,
    ).select_related("student", "assignment", "assignment__module__level")
    return render(request, "instructor/assignments.html", {"submissions": submissions})


@instructor_required
def instructor_submission_grade(request, pk):
    sub = get_object_or_404(
        AssignmentSubmission.objects.select_related("assignment__module__level", "student"),
        pk=pk,
    )
    if not instructor_owns_submission(request.user, sub):
        from django.http import Http404
        raise Http404

    if request.method == "POST":
        sub.grade = Decimal(request.POST.get("grade", 0))
        sub.feedback = request.POST.get("feedback", "")
        sub.status = request.POST.get("status", AssignmentSubmission.Status.GRADED)
        sub.save()
        log_audit(request, "assignment_grade", "AssignmentSubmission", sub.pk, sub.assignment.title)
        messages.success(request, "Submission graded.")
        return redirect("instructor:assignments")
    return render(request, "instructor/grade_submission.html", {"submission": sub})
