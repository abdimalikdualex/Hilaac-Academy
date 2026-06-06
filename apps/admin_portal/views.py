from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.assessments.models import Assignment, AssignmentSubmission, Quiz, QuizAttempt
from apps.certificates.models import Certificate
from apps.certificates.services import maybe_issue_certificate
from apps.cms.models import FAQ, SiteStatistic, Testimonial
from apps.core.models import AuditLog, SiteSettings
from apps.core.utils import log_audit
from apps.courses.models import Enrollment, Language, Lesson, Level, Module
from apps.learning.models import LessonProgress
from apps.library.models import LibraryResource
from apps.notifications.models import Notification
from apps.payments.currency import format_payment_display, revenue_totals
from apps.payments.models import ExchangeRate, Payment

from .decorators import super_admin_required
from .forms import (
    ExchangeRateForm,
    FAQForm,
    InstructorForm,
    LevelForm,
    LibraryResourceForm,
    SiteSettingsForm,
    StudentForm,
    TestimonialForm,
)

User = get_user_model()


def _recent_activities(limit=15):
    activities = []
    for e in Enrollment.objects.select_related("student", "level").order_by("-enrolled_at")[:5]:
        activities.append({"text": f"{e.student.username} enrolled in {e.level.name}", "date": e.enrolled_at, "type": "enrollment"})
    for p in Payment.objects.filter(status=Payment.Status.COMPLETED).order_by("-verified_at")[:5]:
        if p.verified_at:
            activities.append({"text": f"Payment {format_payment_display(p)} from {p.student.username}", "date": p.verified_at, "type": "payment"})
    for c in Certificate.objects.order_by("-issued_at")[:5]:
        activities.append({"text": f"Certificate issued to {c.student.username}", "date": c.issued_at, "type": "certificate"})
    for log in AuditLog.objects.select_related("user").order_by("-created_at")[:5]:
        activities.append({"text": log.action, "date": log.created_at, "type": "audit"})
    activities.sort(key=lambda x: x["date"], reverse=True)
    return activities[:limit]


@super_admin_required
def dashboard(request):
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_students = User.objects.filter(role=User.Role.STUDENT).count()
    total_instructors = User.objects.filter(role=User.Role.INSTRUCTOR).count()
    total_courses = Level.objects.filter(is_archived=False).count()
    active_enrollments = Enrollment.objects.filter(status=Enrollment.Status.ACTIVE).count()
    completed_payments = Payment.objects.filter(status=Payment.Status.COMPLETED)
    revenue_all = revenue_totals(completed_payments)
    revenue_month = revenue_totals(completed_payments.filter(created_at__gte=month_start))
    total_revenue = revenue_all
    monthly_revenue = revenue_month
    total_certificates = Certificate.objects.filter(is_revoked=False).count()
    assignments_submitted = AssignmentSubmission.objects.count()
    quizzes_completed = QuizAttempt.objects.filter(completed_at__isnull=False).count()

    popular_courses = (
        Level.objects.annotate(cnt=Count("enrollments")).filter(is_archived=False).order_by("-cnt")[:5]
    )
    recent_payments = Payment.objects.select_related("student", "level").order_by("-created_at")[:8]
    new_registrations = User.objects.filter(role=User.Role.STUDENT).order_by("-date_joined")[:8]
    pending_payments = Payment.objects.filter(status=Payment.Status.PENDING).select_related("student", "level")[:10]

    revenue_by_month = (
        Payment.objects.filter(status=Payment.Status.COMPLETED, created_at__gte=now - timedelta(days=365))
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(total=Sum("amount_usd"))
        .order_by("month")
    )
    students_by_month = (
        User.objects.filter(role=User.Role.STUDENT, date_joined__gte=now - timedelta(days=365))
        .annotate(month=TruncMonth("date_joined"))
        .values("month")
        .annotate(total=Count("id"))
        .order_by("month")
    )

    context = {
        "total_students": total_students,
        "total_instructors": total_instructors,
        "total_courses": total_courses,
        "active_enrollments": active_enrollments,
        "total_revenue": total_revenue,
        "monthly_revenue": monthly_revenue,
        "total_certificates": total_certificates,
        "assignments_submitted": assignments_submitted,
        "quizzes_completed": quizzes_completed,
        "popular_courses": popular_courses,
        "recent_payments": recent_payments,
        "new_registrations": new_registrations,
        "pending_payments": pending_payments,
        "recent_activities": _recent_activities(),
        "revenue_by_month": list(revenue_by_month),
        "students_by_month": list(students_by_month),
    }
    return render(request, "admin_portal/dashboard.html", context)


# --- Students ---
@super_admin_required
def student_list(request):
    from apps.core.pagination import ADMIN_PAGE_SIZE, paginate_queryset

    q = request.GET.get("q", "")
    students = User.objects.filter(role=User.Role.STUDENT)
    if q:
        students = students.filter(
            Q(username__icontains=q)
            | Q(email__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
        )
    page = paginate_queryset(request, students.order_by("-date_joined"), per_page=ADMIN_PAGE_SIZE)
    return render(request, "admin_portal/students/list.html", {"students": page, "page": page, "q": q})


@super_admin_required
def student_create(request):
    if request.method == "POST":
        form = StudentForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = User.Role.STUDENT
            user.set_password(request.POST.get("password", "changeme123"))
            user.save()
            messages.success(request, "Student created.")
            return redirect("admin_portal:student_list")
    else:
        form = StudentForm()
    return render(request, "admin_portal/students/form.html", {"form": form, "title": "Add Student"})


@super_admin_required
def student_edit(request, pk):
    student = get_object_or_404(User, pk=pk, role=User.Role.STUDENT)
    if request.method == "POST":
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            if request.POST.get("password"):
                student.set_password(request.POST["password"])
                student.save()
            messages.success(request, "Student updated.")
            return redirect("admin_portal:student_detail", pk=pk)
    else:
        form = StudentForm(instance=student)
    return render(request, "admin_portal/students/form.html", {"form": form, "title": "Edit Student", "student": student})


@super_admin_required
def student_detail(request, pk):
    student = get_object_or_404(User, pk=pk, role=User.Role.STUDENT)
    enrollments = Enrollment.objects.filter(student=student).select_related("level", "level__language")
    certificates = Certificate.objects.filter(student=student, is_revoked=False)
    quiz_attempts = QuizAttempt.objects.filter(student=student).select_related("quiz")[:20]
    return render(
        request,
        "admin_portal/students/detail.html",
        {"student": student, "enrollments": enrollments, "certificates": certificates, "quiz_attempts": quiz_attempts},
    )


@super_admin_required
def student_toggle_active(request, pk):
    student = get_object_or_404(User, pk=pk, role=User.Role.STUDENT)
    student.is_active = not student.is_active
    student.save(update_fields=["is_active"])
    messages.success(request, f"Student {'activated' if student.is_active else 'suspended'}.")
    return redirect("admin_portal:student_detail", pk=pk)


# --- Instructors ---
@super_admin_required
def instructor_list(request):
    instructors = User.objects.filter(role=User.Role.INSTRUCTOR).annotate(
        course_count=Count("assigned_levels")
    )
    return render(request, "admin_portal/instructors/list.html", {"instructors": instructors})


@super_admin_required
def instructor_create(request):
    if request.method == "POST":
        form = InstructorForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = User.Role.INSTRUCTOR
            user.is_verified = True
            user.set_password(request.POST.get("password", "instructor123"))
            user.save()
            messages.success(request, "Instructor created.")
            return redirect("admin_portal:instructor_list")
    else:
        form = InstructorForm()
    return render(request, "admin_portal/instructors/form.html", {"form": form, "title": "Add Instructor"})


@super_admin_required
def instructor_edit(request, pk):
    instructor = get_object_or_404(User, pk=pk, role=User.Role.INSTRUCTOR)
    if request.method == "POST":
        form = InstructorForm(request.POST, instance=instructor)
        if form.is_valid():
            form.save()
            if request.POST.get("password"):
                instructor.set_password(request.POST["password"])
                instructor.save()
            messages.success(request, "Instructor updated.")
            return redirect("admin_portal:instructor_list")
    else:
        form = InstructorForm(instance=instructor)
    return render(request, "admin_portal/instructors/form.html", {"form": form, "title": "Edit Instructor", "instructor": instructor})


# --- Courses ---
@super_admin_required
def course_list(request):
    levels = Level.objects.select_related("language", "instructor").annotate(
        enrolled_count=Count("enrollments")
    ).order_by("language__name", "order")
    return render(request, "admin_portal/courses/list.html", {"levels": levels})


@super_admin_required
def course_create(request):
    if request.method == "POST":
        form = LevelForm(request.POST, request.FILES)
        if form.is_valid():
            level = form.save()
            log_audit(request, "course_create", "Level", level.pk, level.name)
            messages.success(request, "Course created. Add sections and lessons next.")
            return redirect("courses_manage:level_detail", level_id=level.id)
    else:
        form = LevelForm()
    return render(request, "admin_portal/courses/form.html", {"form": form, "title": "Create Course", "builder_step": 1})


@super_admin_required
def course_edit(request, pk):
    level = get_object_or_404(Level, pk=pk)
    if request.method == "POST":
        form = LevelForm(request.POST, request.FILES, instance=level)
        if form.is_valid():
            form.save()
            log_audit(request, "course_update", "Level", level.pk, str(level))
            messages.success(request, "Course updated.")
            return redirect("courses_manage:level_detail", level_id=level.id)
    else:
        form = LevelForm(instance=level)
    return render(request, "admin_portal/courses/form.html", {"form": form, "title": "Edit Course", "level": level, "builder_step": 1})


@super_admin_required
def course_delete(request, pk):
    level = get_object_or_404(Level, pk=pk)
    if request.method == "POST":
        name = str(level)
        level_id = level.pk
        level.soft_delete(user=request.user)
        log_audit(request, "course_soft_delete", "Level", level_id, name)
        messages.success(request, f"Course '{name}' moved to Recycle Bin.")
        return redirect("admin_portal:course_list")
    enrolled = level.enrollments.count()
    return render(
        request,
        "admin_portal/confirm_delete.html",
        {
            "object_name": "Course",
            "object_label": str(level),
            "warning": f"This moves the course to the Recycle Bin for 30 days. Enrollments ({enrolled}) are preserved until permanent deletion.",
            "cancel_url": reverse("admin_portal:course_list"),
        },
    )


@super_admin_required
def course_toggle_publish(request, pk):
    level = get_object_or_404(Level, pk=pk)
    level.is_published = not level.is_published
    level.save(update_fields=["is_published"])
    log_audit(request, "course_publish_toggle", "Level", level.pk, f"published={level.is_published}")
    messages.success(request, f"Course {'published' if level.is_published else 'unpublished'}.")
    return redirect("admin_portal:course_list")


@super_admin_required
def course_archive(request, pk):
    level = get_object_or_404(Level, pk=pk)
    level.is_archived = not level.is_archived
    level.is_published = False if level.is_archived else level.is_published
    level.save(update_fields=["is_archived", "is_published"])
    log_audit(request, "course_archive_toggle", "Level", level.pk, f"archived={level.is_archived}")
    messages.success(request, f"Course {'archived' if level.is_archived else 'restored'}.")
    return redirect("admin_portal:course_list")


# --- Enrollments ---
@super_admin_required
def enrollment_list(request):
    enrollments = Enrollment.objects.select_related("student", "level", "level__language").order_by("-enrolled_at")
    students = User.objects.filter(role=User.Role.STUDENT, is_active=True)
    levels = Level.objects.filter(is_published=True, is_archived=False)
    return render(
        request,
        "admin_portal/enrollments/list.html",
        {"enrollments": enrollments, "students": students, "levels": levels},
    )


@super_admin_required
def enrollment_create(request):
    if request.method == "POST":
        student_id = request.POST.get("student")
        level_id = request.POST.get("level")
        student = get_object_or_404(User, pk=student_id, role=User.Role.STUDENT)
        level = get_object_or_404(Level, pk=level_id)
        Enrollment.objects.get_or_create(student=student, level=level, defaults={"status": Enrollment.Status.ACTIVE})
        messages.success(request, "Student enrolled manually.")
        return redirect("admin_portal:enrollment_list")
    return redirect("admin_portal:enrollment_list")


@super_admin_required
def enrollment_delete(request, pk):
    enrollment = get_object_or_404(Enrollment, pk=pk)
    enrollment.delete()
    messages.success(request, "Enrollment removed.")
    return redirect("admin_portal:enrollment_list")


# --- Payments ---
@super_admin_required
def payment_list(request):
    status = request.GET.get("status", "")
    payments = Payment.objects.select_related("student", "level").order_by("-created_at")
    if status:
        payments = payments.filter(status=status)
    return render(request, "admin_portal/payments/list.html", {"payments": payments, "status": status})


@super_admin_required
def payment_approve(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    payment.approve()
    log_audit(request, "payment_approve", "Payment", payment.pk, f"student={payment.student_id}")
    messages.success(request, "Payment approved and student enrolled.")
    return redirect("admin_portal:payment_list")


@super_admin_required
def payment_refund(request, pk):
    payment = get_object_or_404(Payment, pk=pk, status=Payment.Status.COMPLETED)
    if request.method == "POST":
        note = request.POST.get("note", "Refunded by admin")
        payment.refund(note)
        log_audit(request, "payment_refund", "Payment", payment.pk, note)
        messages.success(request, "Payment refunded and course access revoked.")
        return redirect("admin_portal:payment_list")
    return render(
        request,
        "admin_portal/confirm_delete.html",
        {
            "object_name": "Refund Payment",
            "object_label": f"{payment.student.username} — {payment.level.name} ({format_payment_display(payment)})",
            "warning": "This will revoke the student's enrollment for this course.",
            "cancel_url": reverse("admin_portal:payment_list"),
        },
    )


@super_admin_required
@require_POST
def payment_reject(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    note = request.POST.get("note", "") if request.method == "POST" else ""
    payment.reject(note=note)
    messages.success(request, "Payment rejected. The student has been notified.")
    return redirect("admin_portal:payment_list")


# --- Certificates ---
@super_admin_required
def certificate_list(request):
    certificates = Certificate.objects.select_related("student", "level", "level__language").order_by("-issued_at")
    return render(request, "admin_portal/certificates/list.html", {"certificates": certificates})


@super_admin_required
def certificate_revoke(request, pk):
    cert = get_object_or_404(Certificate, pk=pk)
    cert.is_revoked = True
    cert.revoked_at = timezone.now()
    cert.save(update_fields=["is_revoked", "revoked_at"])
    messages.success(request, "Certificate revoked.")
    return redirect("admin_portal:certificate_list")


@super_admin_required
def certificate_generate(request):
    if request.method == "POST":
        student = get_object_or_404(User, pk=request.POST["student"], role=User.Role.STUDENT)
        level = get_object_or_404(Level, pk=request.POST["level"])
        cert = maybe_issue_certificate(student, level)
        if cert:
            messages.success(request, f"Certificate {cert.certificate_id} generated.")
        else:
            messages.error(request, "Could not generate — student must complete all lessons and pass final exam.")
    students = User.objects.filter(role=User.Role.STUDENT)
    levels = Level.objects.filter(is_published=True)
    return render(request, "admin_portal/certificates/generate.html", {"students": students, "levels": levels})


# --- Quizzes & Assignments ---
@super_admin_required
def quiz_list(request):
    quizzes = Quiz.objects.select_related("module", "level", "module__level").order_by("-created_at")
    return render(request, "admin_portal/quizzes/list.html", {"quizzes": quizzes})


@super_admin_required
def assignment_list(request):
    assignments = Assignment.objects.select_related("module", "module__level").order_by("-created_at")
    submissions = AssignmentSubmission.objects.select_related("student", "assignment").order_by("-submitted_at")[:20]
    return render(
        request,
        "admin_portal/assignments/list.html",
        {"assignments": assignments, "submissions": submissions},
    )


@super_admin_required
def submission_grade(request, pk):
    sub = get_object_or_404(AssignmentSubmission, pk=pk)
    if request.method == "POST":
        sub.grade = Decimal(request.POST.get("grade", 0))
        sub.feedback = request.POST.get("feedback", "")
        sub.status = request.POST.get("status", AssignmentSubmission.Status.GRADED)
        sub.save()
        log_audit(request, "assignment_grade", "AssignmentSubmission", sub.pk, sub.assignment.title)
        messages.success(request, "Submission graded.")
        return redirect("admin_portal:assignment_list")
    return render(request, "admin_portal/assignments/grade.html", {"submission": sub})


# --- Library ---
@super_admin_required
def library_list(request):
    resources = LibraryResource.objects.select_related("language").order_by("-created_at")
    return render(request, "admin_portal/library/list.html", {"resources": resources})


@super_admin_required
def library_create(request):
    if request.method == "POST":
        form = LibraryResourceForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Resource uploaded.")
            return redirect("admin_portal:library_list")
    else:
        form = LibraryResourceForm()
    return render(request, "admin_portal/library/form.html", {"form": form, "title": "Upload Resource"})


# --- Reports ---
@super_admin_required
def reports(request):
    total_students = User.objects.filter(role=User.Role.STUDENT).count()
    completed = Enrollment.objects.filter(status=Enrollment.Status.COMPLETED).count()
    total_enrollments = Enrollment.objects.count()
    completion_rate = round((completed / total_enrollments * 100) if total_enrollments else 0, 1)

    now = timezone.now()
    completed = Payment.objects.filter(status=Payment.Status.COMPLETED)
    daily_revenue = revenue_totals(completed.filter(created_at__date=now.date()))
    monthly_revenue = revenue_totals(
        completed.filter(created_at__month=now.month, created_at__year=now.year)
    )
    annual_revenue = revenue_totals(completed.filter(created_at__year=now.year))
    payment_method_breakdown = (
        completed.values("method")
        .annotate(count=Count("id"), usd_total=Sum("amount_usd"))
        .order_by("-count")
    )

    course_stats = Level.objects.annotate(
        enrollments_count=Count("enrollments"),
        completions=Count("enrollments", filter=Q(enrollments__status=Enrollment.Status.COMPLETED)),
    ).filter(is_archived=False)[:10]

    top_preview_lessons = (
        Lesson.objects.filter(is_preview=True, preview_views__gt=0)
        .select_related("module__level__language")
        .order_by("-preview_views")[:10]
    )
    preview_courses = (
        Level.objects.filter(is_published=True, is_archived=False)
        .annotate(
            preview_views_total=Sum("modules__lessons__preview_views"),
            preview_count=Count("modules__lessons", filter=Q(modules__lessons__is_preview=True)),
            enrollments_count=Count("enrollments"),
        )
        .filter(preview_count__gt=0)
        .order_by("-preview_views_total")[:10]
    )

    return render(
        request,
        "admin_portal/reports.html",
        {
            "total_students": total_students,
            "completion_rate": completion_rate,
            "daily_revenue": daily_revenue,
            "monthly_revenue": monthly_revenue,
            "annual_revenue": annual_revenue,
            "payment_method_breakdown": payment_method_breakdown,
            "course_stats": course_stats,
            "top_preview_lessons": top_preview_lessons,
            "preview_courses": preview_courses,
        },
    )


@super_admin_required
def cms_home(request):
    return render(
        request,
        "admin_portal/cms/home.html",
        {
            "statistics": SiteStatistic.objects.all(),
            "testimonials": Testimonial.objects.all(),
            "faqs": FAQ.objects.all(),
        },
    )


@super_admin_required
def cms_faq_edit(request, pk=None):
    faq = get_object_or_404(FAQ, pk=pk) if pk is not None else None
    if request.method == "POST":
        form = FAQForm(request.POST, instance=faq)
        if form.is_valid():
            form.save()
            messages.success(request, "FAQ saved.")
            return redirect("admin_portal:cms_home")
    else:
        form = FAQForm(instance=faq)
    return render(request, "admin_portal/cms/faq_form.html", {"form": form})


@super_admin_required
def exchange_rates(request):
    rates = ExchangeRate.objects.order_by("to_currency")
    edit_pk = request.GET.get("edit")
    editing = get_object_or_404(ExchangeRate, pk=edit_pk) if edit_pk else None

    if request.method == "POST":
        if request.POST.get("action") == "delete":
            rate = get_object_or_404(ExchangeRate, pk=request.POST.get("pk"))
            rate.delete()
            messages.success(request, f"Removed {rate.to_currency} rate.")
            return redirect("admin_portal:exchange_rates")

        instance = editing
        if not instance and request.POST.get("pk"):
            instance = get_object_or_404(ExchangeRate, pk=request.POST.get("pk"))
        form = ExchangeRateForm(request.POST, instance=instance)
        if form.is_valid():
            rate = form.save(commit=False)
            rate.from_currency = "USD"
            rate.save()
            messages.success(request, f"Saved USD → {rate.to_currency} rate.")
            return redirect("admin_portal:exchange_rates")
    else:
        form = ExchangeRateForm(instance=editing)

    return render(
        request,
        "admin_portal/exchange_rates.html",
        {"rates": rates, "form": form, "editing": editing},
    )


@super_admin_required
def settings_view(request):
    site = SiteSettings.get()
    if request.method == "POST":
        form = SiteSettingsForm(request.POST, request.FILES, instance=site)
        if form.is_valid():
            form.save()
            log_audit(request, "site_settings_update", "SiteSettings", site.pk, site.academy_name)
            messages.success(request, "Settings saved.")
            return redirect("admin_portal:settings")
    else:
        form = SiteSettingsForm(instance=site)
    return render(request, "admin_portal/settings.html", {"form": form})


@super_admin_required
def notification_list(request):
    from apps.core.pagination import NOTIFICATION_PAGE_SIZE, paginate_queryset

    notifications = Notification.objects.select_related("user").order_by("-created_at")
    page = paginate_queryset(request, notifications, per_page=NOTIFICATION_PAGE_SIZE)
    return render(request, "admin_portal/notifications/list.html", {"notifications": page, "page": page})


# --- Delete (super admin can remove anything) ---
@super_admin_required
def student_delete(request, pk):
    student = get_object_or_404(User, pk=pk, role=User.Role.STUDENT)
    if request.method == "POST":
        name = student.username
        student.delete()
        log_audit(request, "student_delete", "User", pk, name)
        messages.success(request, f"Student '{name}' deleted.")
        return redirect("admin_portal:student_list")
    return render(
        request,
        "admin_portal/confirm_delete.html",
        {"object_name": "Student", "object_label": student.get_full_name() or student.username, "cancel_url": reverse("admin_portal:student_list")},
    )


@super_admin_required
def instructor_delete(request, pk):
    instructor = get_object_or_404(User, pk=pk, role=User.Role.INSTRUCTOR)
    if request.method == "POST":
        name = instructor.username
        instructor.delete()
        log_audit(request, "instructor_delete", "User", pk, name)
        messages.success(request, f"Instructor '{name}' deleted.")
        return redirect("admin_portal:instructor_list")
    return render(
        request,
        "admin_portal/confirm_delete.html",
        {"object_name": "Instructor", "object_label": instructor.get_full_name() or instructor.username, "cancel_url": reverse("admin_portal:instructor_list")},
    )


@super_admin_required
def library_delete(request, pk):
    resource = get_object_or_404(LibraryResource, pk=pk)
    if request.method == "POST":
        title = resource.title
        resource.soft_delete(user=request.user)
        log_audit(request, "library_soft_delete", "LibraryResource", pk, title)
        messages.success(request, f"Resource '{title}' moved to Recycle Bin.")
        return redirect("admin_portal:library_list")
    return render(
        request,
        "admin_portal/confirm_delete.html",
        {"object_name": "Library Resource", "object_label": resource.title, "cancel_url": reverse("admin_portal:library_list")},
    )


@super_admin_required
def faq_delete(request, pk):
    faq = get_object_or_404(FAQ, pk=pk)
    if request.method == "POST":
        question = faq.question
        faq.delete()
        log_audit(request, "faq_delete", "FAQ", pk, question)
        messages.success(request, "FAQ deleted.")
        return redirect("admin_portal:cms_home")
    return render(
        request,
        "admin_portal/confirm_delete.html",
        {"object_name": "FAQ", "object_label": faq.question, "cancel_url": reverse("admin_portal:cms_home")},
    )


@super_admin_required
def quiz_delete(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk)
    if request.method == "POST":
        title = quiz.title
        quiz.delete()
        log_audit(request, "quiz_delete", "Quiz", pk, title)
        messages.success(request, f"Quiz '{title}' deleted.")
        return redirect("admin_portal:quiz_list")
    return render(
        request,
        "admin_portal/confirm_delete.html",
        {"object_name": "Quiz", "object_label": quiz.title, "cancel_url": reverse("admin_portal:quiz_list")},
    )


@super_admin_required
def assignment_delete(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)
    if request.method == "POST":
        title = assignment.title
        assignment.delete()
        log_audit(request, "assignment_delete", "Assignment", pk, title)
        messages.success(request, f"Assignment '{title}' deleted.")
        return redirect("admin_portal:assignment_list")
    return render(
        request,
        "admin_portal/confirm_delete.html",
        {"object_name": "Assignment", "object_label": assignment.title, "cancel_url": reverse("admin_portal:assignment_list")},
    )


@super_admin_required
def certificate_delete(request, pk):
    cert = get_object_or_404(Certificate, pk=pk)
    if request.method == "POST":
        cert_id = cert.certificate_id
        cert.delete()
        log_audit(request, "certificate_delete", "Certificate", pk, cert_id)
        messages.success(request, f"Certificate '{cert_id}' deleted.")
        return redirect("admin_portal:certificate_list")
    return render(
        request,
        "admin_portal/confirm_delete.html",
        {"object_name": "Certificate", "object_label": cert.certificate_id, "cancel_url": reverse("admin_portal:certificate_list")},
    )