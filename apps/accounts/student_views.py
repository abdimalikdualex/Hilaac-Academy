from django.contrib import messages
from django.contrib.auth.views import PasswordChangeView
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

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

from .forms import ProfileForm


@student_required
def dashboard(request):
    return render(request, "student/dashboard.html", student_dashboard_context(request.user))


@student_required
def dashboard_stats_partial(request):
    return render(request, "student/partials/dashboard_stats.html", student_dashboard_stats(request.user))


@student_required
def my_courses(request):
    enrollments = (
        Enrollment.objects.filter(student=request.user)
        .exclude(status=Enrollment.Status.CANCELLED)
        .select_related("level", "level__language")
        .order_by("-enrolled_at")
    )
    enrolled_level_ids = set(enrollments.values_list("level_id", flat=True))
    pending_payments = (
        Payment.objects.filter(student=request.user, status=Payment.Status.PENDING)
        .exclude(level_id__in=enrolled_level_ids)
        .select_related("level", "level__language")
        .order_by("-created_at")
    )
    course_items = []
    for payment in pending_payments:
        course_items.append(
            {
                "kind": "pending",
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
        Enrollment.objects.filter(student=request.user, status=Enrollment.Status.ACTIVE)
        .select_related("level", "level__language")
        .order_by("-enrolled_at")
    )
    return render(request, "student/continue_learning.html", {"active_enrollments": active})


@student_required
def assignments(request):
    enrolled_level_ids = Enrollment.objects.filter(
        student=request.user, status=Enrollment.Status.ACTIVE
    ).values_list("level_id", flat=True)
    assignments_qs = (
        Assignment.objects.filter(
            module__level_id__in=enrolled_level_ids,
            is_published=True,
        )
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
    enrolled_level_ids = Enrollment.objects.filter(student=request.user).values_list("level_id", flat=True)
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
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("student:profile")
    else:
        form = ProfileForm(instance=request.user)
    return render(request, "student/profile.html", {"form": form})


class StudentPortalPasswordChangeView(PasswordChangeView):
    template_name = "student/password_change.html"
    success_url = reverse_lazy("student:settings")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_student:
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied
        from django.conf import settings

        if settings.REQUIRE_EMAIL_VERIFICATION and not request.user.is_verified:
            messages.warning(request, "Please verify your email before changing your password.")
            return redirect("accounts:verify_notice")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, "Password changed successfully.")
        return super().form_valid(form)


@student_required
def wishlist(request):
    items = Wishlist.objects.filter(student=request.user).select_related("level", "level__language")
    return render(request, "student/wishlist.html", {"items": items})


@student_required
def settings(request):
    return render(request, "student/settings.html", {"password_form": None})
