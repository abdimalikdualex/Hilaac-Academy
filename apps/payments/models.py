from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class ExchangeRate(TimeStampedModel):
    """Super Admin managed FX rates. Base currency is always USD."""

    from_currency = models.CharField(max_length=3, default="USD")
    to_currency = models.CharField(max_length=4)
    rate = models.DecimalField(max_digits=12, decimal_places=4, help_text="1 USD equals this many units of to_currency")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["to_currency"]
        unique_together = ("from_currency", "to_currency")

    def __str__(self):
        return f"1 {self.from_currency} = {self.rate} {self.to_currency}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from django.core.cache import cache

        cache.delete(f"fx:{self.from_currency}:{self.to_currency}")


class Payment(TimeStampedModel):
    class Method(models.TextChoices):
        MPESA = "mpesa", "M-Pesa"
        EVC_PLUS = "evc_plus", "EVC Plus"
        ZAAD = "zaad", "Zaad"
        SAHAL = "sahal", "Sahal"
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        COMPLETED = "completed", "Approved"
        REJECTED = "rejected", "Rejected"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    student = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="payments")
    level = models.ForeignKey("courses.Level", on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Amount charged in currency")
    amount_usd = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Base course price in USD")
    currency = models.CharField(max_length=4, default="USD")
    exchange_rate = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    method = models.CharField(max_length=20, choices=Method.choices)
    reference = models.CharField(max_length=100, blank=True, help_text="Legacy / internal reference")
    phone_number = models.CharField(max_length=20, blank=True)
    checkout_request_id = models.CharField(max_length=100, blank=True, db_index=True)
    transaction_id = models.CharField(max_length=100, blank=True, help_text="Provider receipt / transaction ID")
    screenshot = models.ImageField(upload_to="payments/screenshots/", blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    verified_at = models.DateTimeField(null=True, blank=True, help_text="When payment was confirmed by provider")
    approved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_payments",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    receipt_number = models.CharField(max_length=50, unique=True, blank=True)
    admin_note = models.TextField(blank=True)
    failure_message = models.TextField(blank=True)
    provider_message = models.CharField(max_length=255, blank=True, help_text="Message shown to student after push")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["student", "level", "status"]),
        ]

    def __str__(self):
        return f"{self.student} - {self.level} ({self.status})"

    @property
    def screenshot_url(self):
        from apps.core.protected_media import protected_url

        return protected_url(self.screenshot)

    @property
    def mpesa_receipt_number(self):
        """M-Pesa receipt from STK callback (stored in transaction_id)."""
        if self.method == self.Method.MPESA and self.transaction_id:
            return self.transaction_id
        return ""

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = f"HA-RCP-{timezone.now().strftime('%Y%m%d%H%M%S')}-{self.student_id or 0}"
        super().save(*args, **kwargs)

    @classmethod
    def get_active_pending(cls, student, level):
        return cls.objects.filter(
            student=student, level=level, status=cls.Status.PENDING
        ).order_by("-created_at").first()

    @classmethod
    def get_awaiting_approval(cls, student, level):
        return cls.objects.filter(
            student=student, level=level, status=cls.Status.PAID
        ).order_by("-created_at").first()

    @classmethod
    def get_blocking_payment(cls, student, level):
        """Payment in progress or awaiting admin approval."""
        return cls.objects.filter(
            student=student,
            level=level,
            status__in=[cls.Status.PENDING, cls.Status.PAID],
        ).order_by("-created_at").first()

    def mark_paid(self, transaction_id=None):
        """M-Pesa (or provider) confirmed payment — awaits admin approval."""
        if self.status not in (self.Status.PENDING,):
            return False

        from apps.notifications.services import notify_admin_payment_requires_approval, notify_payment_received

        update_fields = ["status", "verified_at"]
        if transaction_id:
            self.transaction_id = transaction_id
            update_fields.append("transaction_id")
        self.status = self.Status.PAID
        self.verified_at = timezone.now()
        self.save(update_fields=update_fields)

        notify_payment_received(self)
        notify_admin_payment_requires_approval(self)
        return True

    def approve(self, approved_by=None):
        """Admin grants course access after payment verification."""
        if self.status == self.Status.COMPLETED:
            return False
        if self.status not in (self.Status.PAID, self.Status.PENDING):
            return False

        from apps.courses.models import Enrollment
        from apps.notifications.services import notify_access_activated, notify_enrollment

        self.status = self.Status.COMPLETED
        if approved_by:
            self.approved_by = approved_by
        self.approved_at = timezone.now()
        if not self.verified_at:
            self.verified_at = self.approved_at
        self.save(update_fields=["status", "approved_by", "approved_at", "verified_at"])

        enrollment, created = Enrollment.objects.get_or_create(
            student=self.student,
            level=self.level,
            defaults={
                "status": Enrollment.Status.ACTIVE,
                "access_granted": True,
                "payment_verified": True,
            },
        )
        if not created:
            enrollment.status = Enrollment.Status.ACTIVE
            enrollment.access_granted = True
            enrollment.payment_verified = True
            enrollment.save(update_fields=["status", "access_granted", "payment_verified"])

        notify_access_activated(self)
        notify_enrollment(self.student, self.level)
        return True

    def mark_failed(self, message="Payment was not completed."):
        if self.status != self.Status.PENDING:
            return
        self.status = self.Status.FAILED
        self.failure_message = message[:500]
        self.save(update_fields=["status", "failure_message"])

    def mark_cancelled(self, message="Payment cancelled."):
        if self.status != self.Status.PENDING:
            return
        self.status = self.Status.CANCELLED
        self.failure_message = message[:500]
        self.save(update_fields=["status", "failure_message"])

    def reject(self, note=""):
        from apps.notifications.services import notify_payment_rejected

        self.status = self.Status.REJECTED
        if note:
            self.admin_note = note
        self.save(update_fields=["status", "admin_note"])
        notify_payment_rejected(self)

    def refund(self, note=""):
        from apps.courses.models import Enrollment

        self.status = self.Status.REFUNDED
        if note:
            self.admin_note = note
        self.save(update_fields=["status", "admin_note"])
        Enrollment.objects.filter(student=self.student, level=self.level).update(
            status=Enrollment.Status.CANCELLED,
            access_granted=False,
            payment_verified=False,
        )
