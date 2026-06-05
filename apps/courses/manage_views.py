from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.utils import log_audit

from .forms import LessonForm, ModuleForm
from .models import Language, Lesson, Level, Module


def is_super_admin(user):
    return user.is_authenticated and user.is_super_admin


@login_required
@user_passes_test(is_super_admin)
def course_manager(request):
    languages = Language.objects.filter(is_active=True).prefetch_related("levels")
    levels = Level.objects.select_related("language").order_by("language__name", "order")
    return render(request, "courses/manage/list.html", {"languages": languages, "levels": levels})


@login_required
@user_passes_test(is_super_admin)
def level_detail(request, level_id):
    from apps.courses.analytics import course_analytics
    from apps.courses.preview import get_first_lesson

    level = get_object_or_404(
        Level.objects.select_related("language").prefetch_related("modules__lessons"),
        pk=level_id,
    )
    return render(
        request,
        "courses/manage/level_detail.html",
        {
            "level": level,
            "analytics": course_analytics(level),
            "first_lesson": get_first_lesson(level),
            "builder_step": 2,
        },
    )


@login_required
@user_passes_test(is_super_admin)
def module_add(request, level_id):
    level = get_object_or_404(Level, pk=level_id)
    if request.method == "POST":
        form = ModuleForm(request.POST)
        if form.is_valid():
            module = form.save()
            log_audit(request, "module_create", "Module", module.pk, module.title)
            messages.success(request, f"Module '{module.title}' created.")
            return redirect("courses_manage:level_detail", level_id=level.id)
    else:
        next_order = level.modules.count() + 1
        form = ModuleForm(initial={"level": level, "order": next_order})
    return render(request, "courses/manage/module_form.html", {"form": form, "level": level, "builder_step": 2})


@login_required
@user_passes_test(is_super_admin)
def module_edit(request, module_id):
    module = get_object_or_404(Module.objects.select_related("level"), pk=module_id)
    if request.method == "POST":
        form = ModuleForm(request.POST, instance=module)
        if form.is_valid():
            form.save()
            log_audit(request, "module_update", "Module", module.pk, module.title)
            messages.success(request, "Module updated.")
            return redirect("courses_manage:level_detail", level_id=module.level.id)
    else:
        form = ModuleForm(instance=module)
    return render(request, "courses/manage/module_form.html", {"form": form, "level": module.level, "module": module, "builder_step": 2})


@login_required
@user_passes_test(is_super_admin)
def module_delete(request, module_id):
    module = get_object_or_404(Module.objects.select_related("level"), pk=module_id)
    level_id = module.level.id
    if request.method == "POST":
        title = module.title
        module.delete()
        log_audit(request, "module_delete", "Module", module_id, title)
        messages.success(request, f"Module '{title}' deleted.")
        return redirect("courses_manage:level_detail", level_id=level_id)
    return render(request, "courses/manage/module_confirm_delete.html", {"module": module, "level": module.level})


def _swap_order(obj, queryset, direction):
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


@login_required
@user_passes_test(is_super_admin)
def module_move(request, module_id, direction):
    module = get_object_or_404(Module.objects.select_related("level"), pk=module_id)
    _swap_order(module, module.level.modules.order_by("order", "id"), direction)
    return redirect("courses_manage:level_detail", level_id=module.level.id)


@login_required
@user_passes_test(is_super_admin)
def lesson_move(request, lesson_id, direction):
    lesson = get_object_or_404(Lesson.objects.select_related("module__level"), pk=lesson_id)
    _swap_order(lesson, lesson.module.lessons.order_by("order", "id"), direction)
    return redirect("courses_manage:level_detail", level_id=lesson.module.level.id)


@login_required
@user_passes_test(is_super_admin)
def lesson_add(request, module_id):
    module = get_object_or_404(Module.objects.select_related("level__language"), pk=module_id)
    if request.method == "POST":
        form = LessonForm(request.POST, request.FILES)
        if form.is_valid():
            lesson = form.save()
            from apps.courses.preview import enforce_single_preview

            enforce_single_preview(module.level)
            log_audit(request, "lesson_create", "Lesson", lesson.pk, lesson.title)
            messages.success(request, f"Lesson '{lesson.title}' added with video/content.")
            return redirect("courses_manage:level_detail", level_id=module.level.id)
    else:
        next_order = module.lessons.count() + 1
        form = LessonForm(initial={"module": module, "order": next_order, "lesson_type": Lesson.LessonType.VIDEO})
    return render(request, "courses/manage/lesson_form.html", {"form": form, "module": module, "level": module.level, "is_edit": False, "builder_step": 3})


@login_required
@user_passes_test(is_super_admin)
def lesson_preview(request, lesson_id):
    lesson = get_object_or_404(Lesson.objects.select_related("module__level__language"), pk=lesson_id)
    return render(request, "courses/lesson_preview.html", {"lesson": lesson, "level": lesson.module.level})


@login_required
@user_passes_test(is_super_admin)
def lesson_delete(request, lesson_id):
    lesson = get_object_or_404(Lesson.objects.select_related("module__level"), pk=lesson_id)
    level_id = lesson.module.level.id
    if request.method == "POST":
        title = lesson.title
        level = lesson.module.level
        lesson.delete()
        from apps.courses.preview import enforce_single_preview

        enforce_single_preview(level)
        log_audit(request, "lesson_delete", "Lesson", lesson_id, title)
        messages.success(request, f"Lesson '{title}' deleted.")
        return redirect("courses_manage:level_detail", level_id=level_id)
    return render(request, "courses/lesson_confirm_delete.html", {"lesson": lesson, "level": lesson.module.level})


@login_required
@user_passes_test(is_super_admin)
def lesson_edit(request, lesson_id):
    lesson = get_object_or_404(Lesson.objects.select_related("module__level__language"), pk=lesson_id)
    if request.method == "POST":
        form = LessonForm(request.POST, request.FILES, instance=lesson)
        if form.is_valid():
            form.save()
            from apps.courses.preview import enforce_single_preview

            enforce_single_preview(lesson.module.level)
            log_audit(request, "lesson_update", "Lesson", lesson.pk, lesson.title)
            messages.success(request, "Lesson updated successfully.")
            return redirect("courses_manage:level_detail", level_id=lesson.module.level.id)
    else:
        form = LessonForm(instance=lesson)
    return render(
        request,
        "courses/manage/lesson_form.html",
        {"form": form, "module": lesson.module, "level": lesson.module.level, "lesson": lesson, "is_edit": True, "builder_step": 3},
    )
