from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .email_utils import branded_subject, render_branded_email
from .models import Notification
from .tasks import dispatch_email_task


def _send_branded_email(recipient_email, subject, title, message, action_url=""):
    text, html = render_branded_email(
        "emails/notification.html",
        {
            "title": title,
            "message": message,
            "action_url": f"{settings.SITE_URL.rstrip('/')}{action_url}" if action_url else "",
        },
    )
    dispatch_email_task(subject=subject, message=text, recipient_email=recipient_email, html_message=html)


def create_notification(user, message, notification_type=Notification.NotificationType.GENERAL, link="", send_email=False):
    notification = Notification.objects.create(
        user=user,
        message=message,
        notification_type=notification_type,
        link=link,
    )
    if send_email and user.email:
        _send_branded_email(
            user.email,
            branded_subject(notification_type.replace("_", " ").title()),
            notification_type.replace("_", " ").title(),
            message,
            link,
        )
    return notification


def send_verification_email(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    verify_url = f"{settings.SITE_URL.rstrip('/')}/accounts/verify/{uid}/{token}/"
    text, html = render_branded_email("emails/verification.html", {"verify_url": verify_url})
    dispatch_email_task(
        subject=branded_subject("Verify Your Email"),
        message=text,
        recipient_email=user.email,
        html_message=html,
    )


def notify_enrollment(student, level):
    create_notification(
        student,
        f"You enrolled in {level.language.name} - {level.name}. Start learning now!",
        Notification.NotificationType.ENROLLMENT,
        link=f"/learning/courses/{level.id}/",
        send_email=True,
    )


def notify_course_completion(student, level):
    create_notification(
        student,
        f"Congratulations! You completed {level.name}. Take the final assessment to earn your certificate.",
        Notification.NotificationType.GENERAL,
        link=f"/learning/courses/{level.id}/",
        send_email=True,
    )


def notify_payment_confirmed(payment):
    create_notification(
        payment.student,
        f"Payment Successful! You now have full access to {payment.level.name}.",
        Notification.NotificationType.PAYMENT,
        link=f"/learning/course/{payment.level.id}/",
        send_email=True,
    )


def notify_payment_rejected(payment):
    create_notification(
        payment.student,
        f"Your payment for {payment.level.name} was rejected. Please contact support or submit a new payment.",
        Notification.NotificationType.PAYMENT,
        link=f"/payments/checkout/{payment.level.id}/",
        send_email=True,
    )


def notify_admin_payment_submitted(payment):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    admins = User.objects.filter(role=User.Role.SUPER_ADMIN, is_active=True)
    message = (
        f"Push payment initiated by {payment.student.username} for {payment.level.name} "
        f"({payment.get_method_display()}, KES {payment.amount}, phone: {payment.phone_number})."
    )
    for admin in admins:
        create_notification(
            admin,
            message,
            Notification.NotificationType.PAYMENT,
            link="/admin-portal/payments/?status=pending",
        )


def notify_admin_payment_completed(payment):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    admins = User.objects.filter(role=User.Role.SUPER_ADMIN, is_active=True)
    txn = payment.transaction_id or payment.checkout_request_id or "—"
    message = (
        f"Payment confirmed: {payment.student.username} enrolled in {payment.level.name} "
        f"via {payment.get_method_display()} (KES {payment.amount}, txn: {txn})."
    )
    for admin in admins:
        create_notification(
            admin,
            message,
            Notification.NotificationType.ENROLLMENT,
            link="/admin-portal/enrollments/",
        )


def notify_payment_welcome(payment):
    create_notification(
        payment.student,
        f"Welcome to {payment.level.name}! Your course is now unlocked. Start learning today.",
        Notification.NotificationType.ENROLLMENT,
        link=f"/learning/course/{payment.level.id}/",
        send_email=True,
    )


def notify_certificate_ready(certificate):
    create_notification(
        certificate.student,
        f"Your certificate for {certificate.level.name} is ready to download!",
        Notification.NotificationType.CERTIFICATE,
        link="/certificates/my/",
        send_email=True,
    )


def notify_quiz_reminder(student, level, progress_pct=0):
    create_notification(
        student,
        f"Reminder: Continue your {level.name} course — you're at {progress_pct}%!",
        Notification.NotificationType.QUIZ,
        link=f"/learning/courses/{level.id}/",
        send_email=True,
    )
