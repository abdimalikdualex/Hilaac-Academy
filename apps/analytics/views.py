from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Sum
from django.shortcuts import render
from django.utils import timezone

from apps.accounts.models import User
from apps.certificates.models import Certificate
from apps.courses.models import Enrollment, Level
from apps.payments.models import Payment


def is_super_admin(user):
    return user.is_authenticated and user.is_super_admin


@login_required
@user_passes_test(is_super_admin)
def admin_dashboard(request):
    total_students = User.objects.filter(role=User.Role.STUDENT).count()
    total_courses = Level.objects.filter(is_published=True).count()
    total_enrollments = Enrollment.objects.count()
    completed_enrollments = Enrollment.objects.filter(status=Enrollment.Status.COMPLETED).count()
    total_certificates = Certificate.objects.count()
    completion_rate = round((completed_enrollments / total_enrollments * 100) if total_enrollments else 0, 1)

    revenue = Payment.objects.filter(status=Payment.Status.COMPLETED).aggregate(total=Sum("amount"))["total"] or 0
    now = timezone.now()
    monthly_revenue = (
        Payment.objects.filter(
            status=Payment.Status.COMPLETED,
            created_at__year=now.year,
            created_at__month=now.month,
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )
    pending_payments = Payment.objects.filter(status=Payment.Status.PENDING).count()

    popular_courses = (
        Level.objects.annotate(enrolled_count=Count("enrollments"))
        .filter(is_published=True)
        .order_by("-enrolled_count")[:5]
    )

    recent_enrollments = Enrollment.objects.select_related("student", "level").order_by("-enrolled_at")[:10]
    pending_payment_list = Payment.objects.filter(status=Payment.Status.PENDING).select_related("student", "level")[:5]

    context = {
        "total_students": total_students,
        "total_courses": total_courses,
        "total_enrollments": total_enrollments,
        "completed_enrollments": completed_enrollments,
        "completion_rate": completion_rate,
        "total_certificates": total_certificates,
        "revenue": revenue,
        "monthly_revenue": monthly_revenue,
        "pending_payments": pending_payments,
        "pending_payment_list": pending_payment_list,
        "popular_courses": popular_courses,
        "recent_enrollments": recent_enrollments,
    }
    return render(request, "analytics/dashboard.html", context)
