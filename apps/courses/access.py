"""Course access and purchase state helpers."""
from apps.courses.models import Enrollment
from apps.payments.models import Payment


def get_course_access(user, level):
    """
    Return access metadata for a student and course.
    access_state: visitor | free | locked | pending | rejected | enrolled | completed
    """
    data = {
        "access_state": "visitor",
        "has_full_access": False,
        "is_enrolled": False,
        "pending_payment": None,
        "rejected_payment": None,
        "can_purchase": False,
        "can_wishlist": False,
        "status_label": "LOCKED",
        "status_color": "gray",
    }

    if level.is_free:
        data["status_label"] = "FREE"
        data["status_color"] = "green"

    if not user.is_authenticated:
        data["access_state"] = "free" if level.is_free else "visitor"
        if level.is_free:
            data["status_label"] = "FREE"
        else:
            data["status_label"] = "LOCKED"
        return data

    if not getattr(user, "is_student", False):
        data["access_state"] = "visitor"
        return data

    data["can_wishlist"] = True

    enrollment = (
        Enrollment.objects.filter(student=user, level=level)
        .exclude(status=Enrollment.Status.CANCELLED)
        .first()
    )
    if enrollment:
        data["is_enrolled"] = True
        data["has_full_access"] = True
        if enrollment.status == Enrollment.Status.COMPLETED:
            data["access_state"] = "completed"
            data["status_label"] = "COMPLETED"
            data["status_color"] = "green"
        else:
            data["access_state"] = "enrolled"
            data["status_label"] = "ACTIVE"
            data["status_color"] = "green"
        data["can_wishlist"] = False
        return data

    pending = (
        Payment.objects.filter(student=user, level=level, status=Payment.Status.PENDING)
        .order_by("-created_at")
        .first()
    )
    if pending:
        data["access_state"] = "pending"
        data["pending_payment"] = pending
        data["status_label"] = "PENDING"
        data["status_color"] = "yellow"
        return data

    failed = (
        Payment.objects.filter(
            student=user, level=level, status__in=[Payment.Status.FAILED, Payment.Status.CANCELLED]
        )
        .order_by("-created_at")
        .first()
    )
    if failed:
        data["access_state"] = "failed"
        data["status_label"] = "PAYMENT FAILED"
        data["status_color"] = "red"
        data["can_purchase"] = True
        return data

    rejected = (
        Payment.objects.filter(student=user, level=level, status=Payment.Status.REJECTED)
        .order_by("-created_at")
        .first()
    )
    if rejected:
        data["access_state"] = "rejected"
        data["rejected_payment"] = rejected
        data["status_label"] = "PAYMENT REJECTED"
        data["status_color"] = "red"
        data["can_purchase"] = True
        return data

    if level.is_free:
        data["access_state"] = "free"
        data["status_label"] = "FREE"
        data["status_color"] = "green"
        data["can_purchase"] = True
    else:
        data["access_state"] = "locked"
        data["status_label"] = "LOCKED"
        data["status_color"] = "gray"
        data["can_purchase"] = True

    return data


def batch_course_access(user, levels):
    """Resolve access for many courses with a constant number of queries."""
    level_list = list(levels)
    result = {}

    if not level_list:
        return result

    if not user.is_authenticated or not getattr(user, "is_student", False):
        for level in level_list:
            result[level.id] = get_course_access(user, level)
        return result

    level_ids = [l.id for l in level_list]
    enrollments = {
        e.level_id: e
        for e in Enrollment.objects.filter(student=user, level_id__in=level_ids).exclude(
            status=Enrollment.Status.CANCELLED
        )
    }
    payments = list(
        Payment.objects.filter(student=user, level_id__in=level_ids).order_by("-created_at")
    )
    payments_by_level = {}
    for payment in payments:
        payments_by_level.setdefault(payment.level_id, []).append(payment)

    for level in level_list:
        data = {
            "access_state": "visitor",
            "has_full_access": False,
            "is_enrolled": False,
            "pending_payment": None,
            "rejected_payment": None,
            "can_purchase": False,
            "can_wishlist": True,
            "status_label": "LOCKED",
            "status_color": "gray",
        }
        if level.is_free:
            data["status_label"] = "FREE"
            data["status_color"] = "green"

        enrollment = enrollments.get(level.id)
        if enrollment:
            data["is_enrolled"] = True
            data["has_full_access"] = True
            data["can_wishlist"] = False
            if enrollment.status == Enrollment.Status.COMPLETED:
                data.update({"access_state": "completed", "status_label": "COMPLETED", "status_color": "green"})
            else:
                data.update({"access_state": "enrolled", "status_label": "ACTIVE", "status_color": "green"})
            result[level.id] = data
            continue

        for payment in payments_by_level.get(level.id, []):
            if payment.status == Payment.Status.PENDING:
                data.update(
                    {
                        "access_state": "pending",
                        "pending_payment": payment,
                        "status_label": "PENDING",
                        "status_color": "yellow",
                        "can_wishlist": True,
                    }
                )
                break
            if payment.status in (Payment.Status.FAILED, Payment.Status.CANCELLED):
                data.update(
                    {
                        "access_state": "failed",
                        "status_label": "PAYMENT FAILED",
                        "status_color": "red",
                        "can_purchase": True,
                    }
                )
                break
            if payment.status == Payment.Status.REJECTED:
                data.update(
                    {
                        "access_state": "rejected",
                        "rejected_payment": payment,
                        "status_label": "PAYMENT REJECTED",
                        "status_color": "red",
                        "can_purchase": True,
                    }
                )
                break

        if data["access_state"] == "visitor":
            if level.is_free:
                data.update({"access_state": "free", "status_label": "FREE", "status_color": "green", "can_purchase": True})
            else:
                data.update({"access_state": "locked", "can_purchase": True})

        result[level.id] = data

    return result


def student_has_full_access(user, level):
    if not user.is_authenticated or not getattr(user, "is_student", False):
        return False
    return Enrollment.objects.filter(
        student=user,
        level=level,
        status__in=[Enrollment.Status.ACTIVE, Enrollment.Status.COMPLETED],
    ).exists()
