from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.utils import OperationalError, ProgrammingError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.permissions import instructor_required, role_required, student_required
from apps.courses.access import student_has_full_access
from apps.courses.models import Enrollment, Level

from .forms import DiscussionReplyForm, DiscussionThreadForm, LiveClassSessionForm
from .models import DiscussionReply, DiscussionThread, LiveClassSession


def _can_access_level(user, level):
    if not user.is_authenticated:
        return False
    if getattr(user, "is_instructor", False) and level.instructor_id == user.id:
        return True
    if getattr(user, "is_super_admin", False):
        return True
    return student_has_full_access(user, level)


def _is_course_staff(user, level):
    return (
        getattr(user, "is_super_admin", False)
        or (getattr(user, "is_instructor", False) and level.instructor_id == user.id)
    )


def _community_layout(user, level):
    is_instructor_owner = getattr(user, "is_instructor", False) and level.instructor_id == user.id
    return {
        "base_template": "instructor/base.html" if is_instructor_owner else "student/base.html",
        "back_url": (
            reverse("instructor:level", kwargs={"level_id": level.id})
            if is_instructor_owner
            else reverse("learning:course_view", kwargs={"level_id": level.id})
        ),
    }


course_member_required = role_required("student", "instructor")


@course_member_required
def course_discussions(request, level_id):
    level = get_object_or_404(Level.objects.select_related("language", "instructor"), pk=level_id)
    if not _can_access_level(request.user, level):
        messages.error(request, "You need course access to view discussions.")
        return redirect("courses:detail", language_slug=level.language.slug, level_slug=level.slug)

    threads = level.discussion_threads.select_related("author").all()
    form = DiscussionThreadForm()
    if request.method == "POST":
        form = DiscussionThreadForm(request.POST)
        if form.is_valid():
            thread = form.save(commit=False)
            thread.level = level
            thread.author = request.user
            thread.save()
            messages.success(request, "Your question has been posted.")
            return redirect("community:thread_detail", thread_id=thread.pk)

    return render(
        request,
        "community/discussions.html",
        {
            "level": level,
            "threads": threads,
            "form": form,
            "is_staff": _is_course_staff(request.user, level),
            **_community_layout(request.user, level),
        },
    )


@course_member_required
def thread_detail(request, thread_id):
    thread = get_object_or_404(
        DiscussionThread.objects.select_related("level__language", "level__instructor", "author"),
        pk=thread_id,
    )
    level = thread.level
    if not _can_access_level(request.user, level):
        raise PermissionDenied

    reply_form = DiscussionReplyForm()
    if request.method == "POST" and not thread.is_locked:
        reply_form = DiscussionReplyForm(request.POST)
        if reply_form.is_valid():
            reply = reply_form.save(commit=False)
            reply.thread = thread
            reply.author = request.user
            reply.is_instructor_reply = _is_course_staff(request.user, level)
            reply.save()
            messages.success(request, "Reply posted.")
            return redirect("community:thread_detail", thread_id=thread.pk)

    replies = thread.replies.select_related("author").all()
    return render(
        request,
        "community/thread_detail.html",
        {
            "thread": thread,
            "level": level,
            "replies": replies,
            "reply_form": reply_form,
            "is_staff": _is_course_staff(request.user, level),
            **_community_layout(request.user, level),
        },
    )


@require_POST
@course_member_required
def thread_pin(request, thread_id):
    thread = get_object_or_404(DiscussionThread.objects.select_related("level"), pk=thread_id)
    if not _is_course_staff(request.user, thread.level):
        raise PermissionDenied
    thread.is_pinned = not thread.is_pinned
    thread.save(update_fields=["is_pinned"])
    return redirect("community:thread_detail", thread_id=thread.pk)


@student_required
def live_classes(request):
    enrolled_ids = Enrollment.objects.filter(
        student=request.user, access_granted=True
    ).exclude(status=Enrollment.Status.CANCELLED).values_list("level_id", flat=True)
    now = timezone.now()
    try:
        upcoming = (
            LiveClassSession.objects.filter(level_id__in=enrolled_ids, is_published=True, starts_at__gte=now)
            .select_related("level", "level__language")
            .order_by("starts_at")
        )
        past = (
            LiveClassSession.objects.filter(level_id__in=enrolled_ids, is_published=True, starts_at__lt=now)
            .select_related("level", "level__language")
            .order_by("-starts_at")[:10]
        )
    except (OperationalError, ProgrammingError):
        messages.warning(request, "Live classes are being set up. Please try again shortly.")
        upcoming = LiveClassSession.objects.none()
        past = LiveClassSession.objects.none()
    live_now = [s for s in upcoming if s.is_live_now]
    return render(
        request,
        "community/live_classes.html",
        {"upcoming": upcoming, "past": past, "live_now": live_now},
    )


@instructor_required
def instructor_live_sessions(request, level_id):
    level = get_object_or_404(Level, pk=level_id, instructor=request.user)
    sessions = level.live_sessions.all()
    form = LiveClassSessionForm()
    if request.method == "POST":
        form = LiveClassSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.level = level
            session.created_by = request.user
            session.save()
            from apps.notifications.services import notify_live_class_scheduled

            notify_live_class_scheduled(session)
            messages.success(request, "Live class scheduled.")
            return redirect("community:instructor_live_sessions", level_id=level.id)
    return render(
        request,
        "community/instructor_live_sessions.html",
        {"level": level, "sessions": sessions, "form": form},
    )
