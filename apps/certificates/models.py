from django.db import models
from django.urls import reverse

from apps.core.models import TimeStampedModel


class Certificate(TimeStampedModel):
    student = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="certificates")
    level = models.ForeignKey("courses.Level", on_delete=models.CASCADE, related_name="certificates")
    certificate_id = models.CharField(max_length=50, unique=True)
    qr_code = models.ImageField(upload_to="certificates/qr/", blank=True, null=True)
    pdf_file = models.FileField(upload_to="certificates/pdf/", blank=True, null=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    is_revoked = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("student", "level")
        ordering = ["-issued_at"]

    def __str__(self):
        return self.certificate_id

    def get_verification_url(self):
        return reverse("certificates:verify", kwargs={"certificate_id": self.certificate_id})
