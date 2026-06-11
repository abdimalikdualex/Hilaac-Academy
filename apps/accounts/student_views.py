from django.contrib import messages
from django.contrib.auth.views import PasswordChangeView
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponsePermanentRedirect
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

from apps.core.utils import log_audit

from .forms import AccountSettingsForm, HilaacPasswordChangeForm, NotificationPreferencesForm
from .profile_helpers import profile_stats_for_user
from .profile_views import handle_profile_update


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
    result = handle_profile_update(request, "student:profile")
    if isinstance(result, (HttpResponseRedirect, HttpResponsePermanentRedirect)):
        return result
    return render(request, "student/profile.html", result)


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
        log_audit(self.request, "profile_password_change", "User", self.request.user.pk)
        messages.success(self.request, "Password changed successfully.")
        return super().form_valid(form)


@student_required
def wishlist(request):
    items = Wishlist.objects.filter(student=request.user).select_related("level", "level__language")
    return render(request, "student/wishlist.html", {"items": items})


@student_required
def settings(request):
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
                return redirect("student:settings")
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
                return redirect("student:settings")

    return render(
        request,
        "student/settings.html",
        {
            "account_form": account_form,
            "notification_form": notification_form,
            "password_form": HilaacPasswordChangeForm(user=user),
            "profile_stats": profile_stats_for_user(user),
        },
    )
