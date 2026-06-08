from django.conf import settings
from django.contrib import messages
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import redirect, render
from apps.core.permissions import get_owned_or_404, student_required

from .models import Certificate


def verify(request, certificate_id):
    try:
        certificate = Certificate.objects.select_related("student", "level", "level__language").get(
            certificate_id=certificate_id
        )
        is_valid = True
    except Certificate.DoesNotExist:
        certificate = None
        is_valid = False

    return render(
        request,
        "certificates/verify.html",
        {"certificate": certificate, "is_valid": is_valid, "certificate_id": certificate_id},
    )


@student_required
def my_certificates(request):
    return redirect("student:certificates")


@student_required
def download_certificate(request, certificate_id):
    if settings.REQUIRE_EMAIL_VERIFICATION and not request.user.is_verified:
        messages.warning(request, "Please verify your email before downloading certificates.")
        return redirect("accounts:verify_notice")
    certificate = get_owned_or_404(Certificate, request.user, "student", certificate_id=certificate_id)
    if not certificate.pdf_file:
        raise Http404("Certificate PDF not available.")

    filename = f"{certificate.certificate_id}.pdf"
    if settings.USE_X_ACCEL_REDIRECT:
        from urllib.parse import quote

        response = HttpResponse()
        del response["Content-Type"]
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["X-Accel-Redirect"] = settings.X_ACCEL_INTERNAL_PREFIX + quote(certificate.pdf_file.name)
        return response

    return FileResponse(certificate.pdf_file.open("rb"), as_attachment=True, filename=filename)
