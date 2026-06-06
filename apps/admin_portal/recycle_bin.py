"""Recycle bin — list, restore, and permanently purge soft-deleted items."""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.soft_delete import RECYCLE_RETENTION_DAYS
from apps.core.utils import log_audit
from apps.courses.models import Lesson, Level, Module
from apps.library.models import LibraryResource

from .decorators import super_admin_required


def _deleted_items():
    courses = list(Level.all_objects.filter(is_deleted=True).select_related("language", "deleted_by"))
    modules = list(Module.all_objects.filter(is_deleted=True).select_related("level", "deleted_by"))
    lessons = list(
        Lesson.all_objects.filter(is_deleted=True).select_related("module__level", "deleted_by")
    )
    library = list(LibraryResource.all_objects.filter(is_deleted=True).select_related("language", "deleted_by"))
    return courses, modules, lessons, library


@super_admin_required
def recycle_bin_list(request):
    courses, modules, lessons, library = _deleted_items()
    total = len(courses) + len(modules) + len(lessons) + len(library)
    return render(
        request,
        "admin_portal/recycle_bin.html",
        {
            "courses": courses,
            "modules": modules,
            "lessons": lessons,
            "library": library,
            "total": total,
            "retention_days": RECYCLE_RETENTION_DAYS,
        },
    )


@super_admin_required
def recycle_bin_restore(request, model_type, pk):
    model_map = {
        "course": Level,
        "module": Module,
        "lesson": Lesson,
        "library": LibraryResource,
    }
    model = model_map.get(model_type)
    if not model:
        messages.error(request, "Invalid item type.")
        return redirect("admin_portal:recycle_bin")

    obj = get_object_or_404(model.all_objects, pk=pk, is_deleted=True)
    label = str(obj)
    obj.restore_from_bin()
    log_audit(request, f"{model_type}_restore", model.__name__, pk, label)
    messages.success(request, f"'{label}' restored.")
    return redirect("admin_portal:recycle_bin")


@super_admin_required
@require_POST
def recycle_bin_purge(request, model_type, pk):
    model_map = {
        "course": Level,
        "module": Module,
        "lesson": Lesson,
        "library": LibraryResource,
    }
    model = model_map.get(model_type)
    if not model:
        messages.error(request, "Invalid item type.")
        return redirect("admin_portal:recycle_bin")

    obj = get_object_or_404(model.all_objects, pk=pk, is_deleted=True)
    label = str(obj)
    obj_id = obj.pk
    obj.delete()
    log_audit(request, f"{model_type}_purge", model.__name__, obj_id, label)
    messages.success(request, f"'{label}' permanently deleted.")
    return redirect("admin_portal:recycle_bin")
