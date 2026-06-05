import io
import uuid

import qrcode
from django.conf import settings
from django.contrib.staticfiles.finders import find
from django.core.files.base import ContentFile
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

from apps.assessments.models import Quiz, QuizAttempt
from apps.courses.models import Enrollment
from apps.learning.models import LessonProgress
from apps.notifications.services import notify_certificate_ready

from .models import Certificate


def _all_lessons_completed(student, level):
    total = level.total_lessons
    if total == 0:
        return False
    completed = LessonProgress.objects.filter(
        student=student,
        lesson__module__level=level,
        is_completed=True,
    ).count()
    return completed >= total


def _final_assessment_passed(student, level):
    final_quiz = Quiz.objects.filter(level=level, is_final=True).first()
    if not final_quiz:
        return True
    return QuizAttempt.objects.filter(student=student, quiz=final_quiz, passed=True).exists()


def generate_certificate_id(level):
    prefix = "HA"
    year = timezone.now().year
    lang_code = level.language.name[:2].upper()
    level_code = level.slug[:4].upper()
    unique = uuid.uuid4().hex[:6].upper()
    return f"{prefix}-{year}-{lang_code}-{level_code}-{unique}"


def generate_pdf(certificate):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    logo_path = find("images/logo.png")
    if logo_path:
        c.drawImage(
            logo_path,
            width / 2 - 2.2 * cm,
            height - 5.5 * cm,
            width=4.4 * cm,
            height=4.4 * cm,
            preserveAspectRatio=True,
            mask="auto",
        )

    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 6.5 * cm, "Hilaac Academy")
    c.setFont("Helvetica", 14)
    c.drawCentredString(width / 2, height - 7.2 * cm, "Certificate of Completion")

    c.setFont("Helvetica-Bold", 22)
    student_name = certificate.student.get_full_name() or certificate.student.username
    c.drawCentredString(width / 2, height - 8.5 * cm, student_name)

    c.setFont("Helvetica", 14)
    c.drawCentredString(
        width / 2,
        height - 10 * cm,
        f"has successfully completed {certificate.level.language.name} - {certificate.level.name}",
    )
    c.drawCentredString(width / 2, height - 11.5 * cm, f"Certificate No: {certificate.certificate_id}")
    c.drawCentredString(width / 2, height - 12.5 * cm, f"Issued: {certificate.issued_at:%B %d, %Y}")

    if certificate.qr_code:
        try:
            c.drawImage(
                certificate.qr_code.path,
                width / 2 - 1.5 * cm,
                2.5 * cm,
                width=3 * cm,
                height=3 * cm,
                preserveAspectRatio=True,
            )
            c.setFont("Helvetica", 9)
            c.drawCentredString(width / 2, 2 * cm, "Scan to verify authenticity")
        except (FileNotFoundError, OSError, ValueError):
            pass

    c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(width / 2, 1.2 * cm, "This certificate is officially issued by Hilaac Academy.")
    c.drawCentredString(width / 2, 0.7 * cm, "Shahaadadan waxaa si rasmi ah u bixisay Hilaac Academy.")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


def generate_qr(certificate):
    verify_url = f"{settings.SITE_URL}{certificate.get_verification_url()}"
    qr = qrcode.make(verify_url)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    return ContentFile(buffer.getvalue(), name=f"qr_{certificate.certificate_id}.png")


def maybe_issue_certificate(student, level):
    from django.conf import settings

    if settings.REQUIRE_EMAIL_VERIFICATION and not getattr(student, "is_verified", False):
        return None

    if Certificate.objects.filter(student=student, level=level).exists():
        return None

    if not _all_lessons_completed(student, level):
        return None

    if not _final_assessment_passed(student, level):
        return None

    certificate = Certificate.objects.create(
        student=student,
        level=level,
        certificate_id=generate_certificate_id(level),
    )

    certificate.qr_code.save(f"qr_{certificate.certificate_id}.png", generate_qr(certificate), save=True)
    pdf_buffer = generate_pdf(certificate)
    certificate.pdf_file.save(f"{certificate.certificate_id}.pdf", ContentFile(pdf_buffer.read()), save=True)

    enrollment = Enrollment.objects.filter(student=student, level=level).first()
    if enrollment:
        enrollment.status = Enrollment.Status.COMPLETED
        enrollment.completed_at = timezone.now()
        enrollment.save()

    notify_certificate_ready(certificate)
    return certificate
