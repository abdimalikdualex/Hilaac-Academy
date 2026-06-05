"""Central RBAC helpers: role decorators and object-level access checks."""
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404


def _user_has_role(user, role):
    if role == "super_admin":
        return user.is_super_admin
    if role == "instructor":
        return user.is_instructor and not user.is_super_admin
    if role == "student":
        return user.is_student and not user.is_super_admin and not user.is_instructor
    return False


def role_required(*roles):
    """Restrict a view to one or more roles. Returns 403 if the wrong role."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not any(_user_has_role(request.user, r) for r in roles):
                raise PermissionDenied("You do not have permission to access this page.")
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


student_required = role_required("student")
instructor_required = role_required("instructor")
super_admin_required = role_required("super_admin")


def get_owned_or_404(model, user, owner_field="student", **lookup):
    """Return an object only if it belongs to the user, else 404 (hide existence)."""
    obj = get_object_or_404(model, **lookup)
    owner = getattr(obj, owner_field, None)
    if owner != user:
        raise Http404
    return obj


def instructor_owns_level(instructor, level):
    return level.instructor_id == instructor.id


def instructor_owns_lesson(instructor, lesson):
    return lesson.module.level.instructor_id == instructor.id


def instructor_owns_submission(instructor, submission):
    return submission.assignment.module.level.instructor_id == instructor.id
