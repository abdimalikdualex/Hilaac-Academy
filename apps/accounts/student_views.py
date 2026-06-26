from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponsePermanentRedirect
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from apps.accounts.password_views import PortalPasswordChangeView

from apps.assessments.models import Assignment, AssignmentSubmission, Quiz, QuizAttempt
from apps.certificates.models import Certificate
from apps.core.dashboard_helpers import student_dashboard_context, student_dashboard_stats
from apps.core.permissions import student_required
from apps.core.roles import role_dashboard_url
from apps.courses.access import get_course_access
from apps.courses.models import Enrollment, Wishlist
from apps.library.models import LibraryResource
from apps.notifications.models import Notification
from apps.payments.models import Payment

from apps.core.utils import log_audit


@student_required
def dashboard(request):
    context = student_dashboard_context(request.user)
    context.update(student_dashboard_stats(request.user))
    return render(request, "student/dashboard.html", context)


@student_required
def dashboard_stats_partial(request):
    return render(request, "student/partials/dashboard_stats.html", student_dashboard_stats(request.user))


@student_required
def my_courses(request):
    enrollments = (
        Enrollment.objects.filter(student=request.user, access_granted=True)
        .exclude(status=Enrollment.Status.CANCELLED)
        .select_related("level", "level__language")
        .order_by("-enrolled_at")
    )
    enrolled_level_ids = set(enrollments.values_list("level_id", flat=True))
    pending_payments = (
        Payment.objects.filter(
            student=request.user,
            status__in=[Payment.Status.PENDING, Payment.Status.PAID],
        )
        .exclude(level_id__in=enrolled_level_ids)
        .select_related("level", "level__language")
        .order_by("-created_at")
    )
    course_items = []
    for payment in pending_payments:
        course_items.append(
            {
                "kind": "pending" if payment.status == Payment.Status.PENDING else "awaiting",
                "level": payment.level,
                "payment": payment,
                "access": get_course_access(request.user, payment.level),
            }
        )
    for enrollment in enrollments:
        course_items.append(
            {
                "kind": "enrolled",
                "level": enrollment.level,
                "enrollment": enrollment,
                "access": get_course_access(request.user, enrollment.level),
            }
        )
    return render(request, "student/courses.html", {"course_items": course_items})


@student_required
def continue_learning(request):
    active = (
        Enrollment.objects.filter(
            student=request.user, status=Enrollment.Status.ACTIVE, access_granted=True
        )
        .select_related("level", "level__language")
        .order_by("-enrolled_at")
    )
    return render(request, "student/continue_learning.html", {"active_enrollments": active})


@student_required
def assignments(request):
    enrolled_level_ids = Enrollment.objects.filter(
        student=request.user, status=Enrollment.Status.ACTIVE, access_granted=True
    ).values_list("level_id", flat=True)
    assignments_qs = (
        Assignment.objects.filter(module__level_id__in=enrolled_level_ids, is_published=True)
        .select_related("module", "module__level", "module__level__language")
        .order_by("due_date")
    )
    submissions = {
        s.assignment_id: s
        for s in AssignmentSubmission.objects.filter(
            student=request.user,
            assignment__in=assignments_qs,
        )
    }
    items = [{"assignment": a, "submission": submissions.get(a.pk)} for a in assignments_qs]
    return render(request, "student/assignments.html", {"items": items})


@student_required
def quizzes(request):
    attempts = (
        QuizAttempt.objects.filter(student=request.user)
        .select_related("quiz", "quiz__level", "quiz__module")
        .order_by("-started_at")
    )
    enrolled_level_ids = Enrollment.objects.filter(
        student=request.user, access_granted=True
    ).exclude(status=Enrollment.Status.CANCELLED).values_list("level_id", flat=True)
    available = Quiz.objects.filter(
        Q(level_id__in=enrolled_level_ids) | Q(module__level_id__in=enrolled_level_ids)
    ).distinct()
    return render(
        request,
        "student/quizzes.html",
        {"attempts": attempts, "available_quizzes": available},
    )


@student_required
def certificates(request):
    certs = Certificate.objects.filter(student=request.user).select_related("level", "level__language")
    return render(request, "student/certificates.html", {"certificates": certs})


@student_required
def library(request):
    from apps.core.pagination import DEFAULT_PAGE_SIZE, paginate_queryset

    resources = LibraryResource.objects.filter(is_published=True).select_related("language").order_by("-created_at")
    page = paginate_queryset(request, resources, per_page=DEFAULT_PAGE_SIZE)
    return render(request, "student/library.html", {"resources": page, "page": page})


@student_required
def notifications(request):
    from apps.core.pagination import NOTIFICATION_PAGE_SIZE, paginate_queryset

    notes = Notification.objects.filter(user=request.user).order_by("-created_at")
    page = paginate_queryset(request, notes, per_page=NOTIFICATION_PAGE_SIZE)
    return render(request, "student/notifications.html", {"notifications": page, "page": page})


@student_required
def profile(request):
    return redirect("student:settings")


class StudentPortalPasswordChangeView(PortalPasswordChangeView):
    settings_url_name = "student:settings"


@student_required
def account_info(request):
    return redirect("student:settings")


@student_required
def preferences(request):
    return redirect("student:settings")


@student_required
def settings(request):
    from .settings_handlers import handle_unified_settings_post, unified_settings_context

    password_form = None
    profile_form = None
    if request.method == "POST":
        result = handle_unified_settings_post(request, "student:settings")
        if result is not None:
            if hasattr(result, "url"):
                return result
            if isinstance(result, dict):
                password_form = result.get("password_form")
                profile_form = result.get("form")
    ctx = unified_settings_context(request, password_form=password_form)
    if profile_form is not None:
        ctx["form"] = profile_form
    return render(request, "student/settings.html", ctx)


@student_required
def wishlist(request):
    items = Wishlist.objects.filter(student=request.user).select_related("level", "level__language")
    return render(request, "student/wishlist.html", {"items": items})
