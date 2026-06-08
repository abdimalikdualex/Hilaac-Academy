"""Authenticated media delivery.

Sensitive uploads (lesson videos/audio/pdf, certificates, payment proofs,
assignment submissions) must never be served directly by Nginx. In production
those folders are marked ``internal`` in Nginx; Django authorizes the request
and hands the file back via ``X-Accel-Redirect``. In development (DEBUG, no
Nginx) the file is streamed directly with ``FileResponse``.
"""
import logging
import posixpath
from urllib.parse import quote

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.urls import reverse

logger = logging.getLogger("hilaac.audit")

# Folders (relative to MEDIA_ROOT) that require an authorization check.
PROTECTED_PREFIXES = (
    "lessons/videos/",
    "lessons/audio/",
    "lessons/pdf/",
    "lessons/resources/",
    "certificates/pdf/",
    "payments/screenshots/",
    "assignments/submissions/",
)


def is_protected(name: str) -> bool:
    name = (name or "").lstrip("/")
    return any(name.startswith(p) for p in PROTECTED_PREFIXES)


def protected_url(field) -> str:
    """URL for a FileField: secured endpoint when enabled, else the raw media URL."""
    if not field:
        return ""
    name = getattr(field, "name", "") or ""
    if settings.USE_X_ACCEL_REDIRECT and is_protected(name):
        return reverse("core:protected_media", kwargs={"path": name})
    try:
        return field.url
    except ValueError:
        return ""


def _can_access(user, path: str) -> bool:
    """Authorize a media path for the given user."""
    from apps.courses.access import student_has_full_access
    from apps.courses.models import Lesson

    if user.is_authenticated and user.is_super_admin:
        return True

    if path.startswith("payments/screenshots/"):
        return False  # super admin only (handled above)

    if path.startswith("certificates/pdf/"):
        from apps.certificates.models import Certificate

        return (
            user.is_authenticated
            and Certificate.objects.filter(student=user, pdf_file__endswith=path.split("/")[-1]).exists()
        )

    if path.startswith("assignments/submissions/"):
        if not user.is_authenticated:
            return False
        from apps.assessments.models import AssignmentSubmission

        fname = path.split("/")[-1]
        sub = AssignmentSubmission.objects.filter(file__endswith=fname).select_related(
            "assignment__module__level"
        ).first()
        if not sub:
            return False
        if getattr(sub, "student_id", None) == user.id:
            return True
        return user.is_instructor and sub.assignment.module.level.instructor_id == user.id

    if path.startswith(("lessons/videos/", "lessons/audio/", "lessons/pdf/", "lessons/resources/")):
        fname = path.split("/")[-1]
        if path.startswith("lessons/resources/"):
            from apps.courses.models import LessonResource

            res = LessonResource.objects.filter(file__endswith=fname).select_related(
                "lesson__module__level"
            ).first()
            lesson = res.lesson if res else None
        else:
            field = {
                "lessons/videos/": "video_file",
                "lessons/audio/": "audio_file",
                "lessons/pdf/": "pdf_file",
            }[next(p for p in (
                "lessons/videos/", "lessons/audio/", "lessons/pdf/") if path.startswith(p))]
            lesson = Lesson.objects.filter(**{f"{field}__endswith": fname}).select_related(
                "module__level"
            ).first()
        if not lesson:
            return False
        level = lesson.module.level
        if lesson.is_preview:
            return True  # free preview is public
        if user.is_authenticated and user.is_instructor and level.instructor_id == user.id:
            return True
        return student_has_full_access(user, level)

    return False


def serve_protected_media(request, path):
    path = posixpath.normpath(path).lstrip("/")
    if ".." in path or not is_protected(path):
        raise Http404

    if not _can_access(request.user, path):
        logger.warning(
            "protected_media_denied user=%s path=%s",
            getattr(request.user, "username", "anonymous"),
            path,
        )
        raise Http404  # hide existence

    if settings.USE_X_ACCEL_REDIRECT:
        response = HttpResponse()
        del response["Content-Type"]  # let Nginx set it
        response["X-Accel-Redirect"] = settings.X_ACCEL_INTERNAL_PREFIX + quote(path)
        return response

    full_path = settings.MEDIA_ROOT / path
    if not full_path.exists():
        raise Http404
    return FileResponse(open(full_path, "rb"))
