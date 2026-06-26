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





def create_notification(

    user,

    message,

    notification_type=Notification.NotificationType.GENERAL,

    link="",

    send_email=False,

    title="",

    severity=Notification.Severity.INFO,

    created_by=None,

    is_system=False,

):

    notification = Notification.objects.create(

        user=user,

        title=title or message[:80],

        message=message,

        notification_type=notification_type,

        severity=severity,

        link=link,

        created_by=created_by,

        is_system=is_system,

    )

    if send_email and user.email:

        _send_branded_email(

            user.email,

            branded_subject(title or notification_type.replace("_", " ").title()),

            title or notification_type.replace("_", " ").title(),

            message,

            link,

        )

    return notification





def send_bulk_notification(

    users,

    title,

    message,

    severity=Notification.Severity.INFO,

    link="",

    created_by=None,

    notification_type=Notification.NotificationType.GENERAL,

):

    created = []

    for user in users:

        created.append(

            create_notification(

                user,

                message,

                notification_type=notification_type,

                link=link,

                title=title,

                severity=severity,

                created_by=created_by,

            )

        )

    return created





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

        link=f"/dashboard/courses/{level.id}/",

        title="Course Enrollment Successful",

        severity=Notification.Severity.SUCCESS,

        is_system=True,

        send_email=True,

    )
    notify_instructor_new_enrollment(level.instructor, student, level)


def notify_instructor_new_enrollment(instructor, student, level):

    if not instructor:

        return

    create_notification(

        instructor,

        f"{student.get_full_name() or student.username} enrolled in {level.name}.",

        Notification.NotificationType.ENROLLMENT,

        link=f"/instructor/courses/{level.id}/students/",

        title="New Student Enrollment",

        severity=Notification.Severity.INFO,

        is_system=True,

    )





def notify_course_completion(student, level):

    create_notification(

        student,

        f"Congratulations! You completed {level.name}. Take the final assessment to earn your certificate.",

        Notification.NotificationType.GENERAL,

        link=f"/dashboard/courses/{level.id}/",

        title="Course Progress Update",

        severity=Notification.Severity.SUCCESS,

        is_system=True,

        send_email=True,

    )





def notify_payment_confirmed(payment):

    create_notification(

        payment.student,

        f"Payment successful. You can now access {payment.level.name}.",

        Notification.NotificationType.PAYMENT,

        link=f"/dashboard/courses/{payment.level.id}/",

        title="Payment Confirmed",

        severity=Notification.Severity.SUCCESS,

        is_system=True,

        send_email=True,

    )





def notify_payment_started(payment):

    create_notification(

        payment.student,

        "Your payment request has been sent. Complete the prompt on your phone.",

        Notification.NotificationType.PAYMENT,

        link=f"/payments/pending/{payment.pk}/",

        title="Payment Started",

        severity=Notification.Severity.INFO,

        is_system=True,

    )





def notify_payment_received(payment):

    create_notification(

        payment.student,

        "Your payment was received. Waiting for admin approval.",

        Notification.NotificationType.PAYMENT,

        link="/dashboard/courses/",

        title="Payment Received",

        severity=Notification.Severity.SUCCESS,

        is_system=True,

        send_email=True,

    )





def notify_access_activated(payment):

    create_notification(

        payment.student,

        f"Your course access has been activated for {payment.level.name}.",

        Notification.NotificationType.PAYMENT,

        link=f"/learning/course/{payment.level.id}/",

        title="Course Access Activated",

        severity=Notification.Severity.SUCCESS,

        is_system=True,

        send_email=True,

    )





def notify_admin_payment_requires_approval(payment):

    from django.contrib.auth import get_user_model

    from apps.payments.currency import format_payment_display

    User = get_user_model()

    admins = User.objects.filter(role=User.Role.SUPER_ADMIN, is_active=True)

    message = (
        f"New course payment requires approval: {payment.student.username} — "
        f"{payment.level.name} ({format_payment_display(payment)}, txn: {payment.transaction_id or 'pending'})"
    )

    for admin in admins:

        create_notification(

            admin,

            message,

            Notification.NotificationType.PAYMENT,

            link="/admin-portal/payments/?status=paid",

            title="Payment Requires Approval",

            severity=Notification.Severity.WARNING,

            is_system=True,

        )





def notify_payment_rejected(payment):

    create_notification(

        payment.student,

        f"Your payment for {payment.level.name} was rejected. Please contact support or submit a new payment.",

        Notification.NotificationType.PAYMENT,

        link=f"/payments/checkout/{payment.level.id}/",

        title="Payment Issue",

        severity=Notification.Severity.WARNING,

        is_system=True,

        send_email=True,

    )





def notify_admin_payment_submitted(payment):

    from django.contrib.auth import get_user_model



    from apps.payments.currency import format_payment_display



    User = get_user_model()

    admins = User.objects.filter(role=User.Role.SUPER_ADMIN, is_active=True)

    message = (

        f"Push payment initiated by {payment.student.username} for {payment.level.name} "

        f"({payment.get_method_display()}, {format_payment_display(payment)}, phone: {payment.phone_number})."

    )

    for admin in admins:

        create_notification(

            admin,

            message,

            Notification.NotificationType.PAYMENT,

            link="/admin-portal/payments/?status=pending",

            title="Payment Received",

            severity=Notification.Severity.INFO,

            is_system=True,

        )





def notify_admin_payment_completed(payment):

    from django.contrib.auth import get_user_model



    from apps.payments.currency import format_payment_display



    User = get_user_model()

    admins = User.objects.filter(role=User.Role.SUPER_ADMIN, is_active=True)

    txn = payment.transaction_id or payment.checkout_request_id or "—"

    message = (

        f"Payment confirmed: {payment.student.username} enrolled in {payment.level.name} "

        f"via {payment.get_method_display()} ({format_payment_display(payment)}, txn: {txn})."

    )

    for admin in admins:

        create_notification(

            admin,

            message,

            Notification.NotificationType.ENROLLMENT,

            link="/admin-portal/enrollments/",

            title="Payment Confirmed",

            severity=Notification.Severity.SUCCESS,

            is_system=True,

        )





def notify_payment_welcome(payment):

    create_notification(

        payment.student,

        f"Welcome to {payment.level.name}! Your course is now unlocked. Start learning today.",

        Notification.NotificationType.ENROLLMENT,

        link=f"/dashboard/courses/{payment.level.id}/",

        title="Welcome to Your Course",

        severity=Notification.Severity.SUCCESS,

        is_system=True,

        send_email=True,

    )





def notify_certificate_ready(certificate):

    create_notification(

        certificate.student,

        f"Your certificate for {certificate.level.name} is ready to download!",

        Notification.NotificationType.CERTIFICATE,

        link="/certificates/my/",

        title="Certificate Issued",

        severity=Notification.Severity.SUCCESS,

        is_system=True,

        send_email=True,

    )





def notify_quiz_reminder(student, level, progress_pct=0):

    create_notification(

        student,

        f"Reminder: Continue your {level.name} course — you're at {progress_pct}%!",

        Notification.NotificationType.QUIZ,

        link=f"/dashboard/courses/{level.id}/",

        title="Quiz Available",

        severity=Notification.Severity.INFO,

        is_system=True,

        send_email=True,

    )





def notify_password_changed(user):
    from apps.core.roles import role_settings_url

    create_notification(
        user,
        "Your password was changed successfully. If you did not make this change, contact support immediately.",
        Notification.NotificationType.SYSTEM,
        link=role_settings_url(user),
        title="Password Changed",
        severity=Notification.Severity.SUCCESS,
        is_system=True,
    )





def notify_assignment_submitted(instructor, submission):

    if not instructor:

        return

    create_notification(

        instructor,

        f"{submission.student.get_full_name() or submission.student.username} submitted {submission.assignment.title}.",

        Notification.NotificationType.ASSIGNMENT,

        link=f"/instructor/assignments/submissions/{submission.pk}/grade/",

        title="Assignment Submitted",

        severity=Notification.Severity.INFO,

        is_system=True,

    )





def notify_assignment_graded(student, submission):

    create_notification(

        student,

        f"Your assignment '{submission.assignment.title}' has been graded: {submission.score_display} marks.",

        Notification.NotificationType.ASSIGNMENT,

        link=f"/quizzes/assignments/{submission.assignment.pk}/",

        title="Assignment Graded",

        severity=Notification.Severity.SUCCESS,

        is_system=True,

    )





def notify_admin_new_user(user):

    from django.contrib.auth import get_user_model



    User = get_user_model()

    admins = User.objects.filter(role=User.Role.SUPER_ADMIN, is_active=True)

    for admin in admins:

        create_notification(

            admin,

            f"New user registered: {user.get_full_name() or user.username} ({user.get_role_display()}).",

            Notification.NotificationType.SYSTEM,

            link=f"/admin-portal/users/?q={user.username}",

            title="New User Registered",

            severity=Notification.Severity.INFO,

            is_system=True,

        )


