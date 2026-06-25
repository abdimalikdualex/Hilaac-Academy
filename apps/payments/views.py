import json
import logging

from django.contrib import messages
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from apps.core.permissions import student_required
from apps.core.utils import log_audit
from apps.courses.access import get_course_access
from apps.courses.models import Level
from apps.notifications.services import notify_admin_payment_submitted

from apps.core.brand_assets import BrandAssetManager

from .constants import PAYMENT_METHOD_META, PAYMENT_SUCCESS_MESSAGE
from .currency import build_payment_amounts, get_checkout_methods_pricing, get_pricing
from .forms import InstantPaymentForm
from .models import Payment
from .services import generate_receipt_pdf, initiate_push_payment, verify_payment_status

logger = logging.getLogger(__name__)


@student_required
def checkout(request, level_id):
    level = get_object_or_404(Level.objects.select_related("language", "instructor"), pk=level_id, is_published=True, is_free=False)
    access = get_course_access(request.user, level)

    if access["has_full_access"]:
        messages.info(request, "You already have access to this course.")
        return redirect("learning:course_view", level_id=level.id)

    pending = Payment.get_active_pending(request.user, level)
    if pending:
        return redirect("payments:pending", payment_id=pending.pk)

    if request.method == "POST":
        form = InstantPaymentForm(request.POST)
        if form.is_valid():
            if Payment.objects.filter(
                student=request.user, level=level, status=Payment.Status.COMPLETED
            ).exists():
                messages.info(request, "You already purchased this course.")
                return redirect("learning:course_view", level_id=level.id)

            amounts = build_payment_amounts(request, level, form.cleaned_data["method"])
            payment = Payment.objects.create(
                student=request.user,
                level=level,
                amount=amounts["amount"],
                amount_usd=amounts["amount_usd"],
                currency=amounts["currency"],
                exchange_rate=amounts["exchange_rate"],
                method=form.cleaned_data["method"],
                phone_number=form.cleaned_data["phone_number"],
                status=Payment.Status.PENDING,
            )

            success, msg, checkout_id = initiate_push_payment(payment)
            if not success:
                payment.mark_failed(msg)
                messages.error(request, msg)
                return redirect("payments:checkout", level_id=level.id)

            notify_admin_payment_submitted(payment)
            log_audit(request, "payment_initiated", "Payment", payment.pk, f"{payment.method} push - {level.name}")
            return redirect("payments:pending", payment_id=payment.pk)
    else:
        form = InstantPaymentForm(initial={"phone_number": request.user.phone or ""})

    pricing = get_pricing(request, level)
    methods_pricing = get_checkout_methods_pricing(request, level)
    return render(
        request,
        "payments/checkout.html",
        {
            "level": level,
            "form": form,
            "pricing": pricing,
            "payment_methods": BrandAssetManager.payment_methods(),
            "payment_methods_json": json.dumps(BrandAssetManager.payment_methods()),
            "methods_pricing_json": json.dumps(methods_pricing),
        },
    )


@student_required
def payment_pending(request, payment_id):
    payment = get_object_or_404(
        Payment.objects.select_related("level", "level__language", "level__instructor"),
        pk=payment_id,
        student=request.user,
    )
    if payment.status == Payment.Status.COMPLETED:
        messages.success(request, PAYMENT_SUCCESS_MESSAGE)
        return redirect("learning:course_view", level_id=payment.level_id)

    pin_message = payment.provider_message or PAYMENT_METHOD_META.get(payment.method, {}).get("pin_message", "")
    return render(
        request,
        "payments/pending.html",
        {"payment": payment, "pin_message": pin_message},
    )


@student_required
@require_GET
def payment_status(request, payment_id):
    payment = get_object_or_404(Payment, pk=payment_id, student=request.user)
    result = verify_payment_status(payment)
    if result["status"] == "completed":
        log_audit(request, "payment_auto_complete", "Payment", payment.pk)
    return JsonResponse(result)


@student_required
def payment_history(request):
    payments = Payment.objects.filter(student=request.user).select_related("level", "level__language")
    return render(request, "payments/history.html", {"payments": payments})


@student_required
def download_receipt(request, payment_id):
    payment = get_object_or_404(Payment, pk=payment_id, student=request.user, status=Payment.Status.COMPLETED)
    pdf_buffer = generate_receipt_pdf(payment)
    return FileResponse(pdf_buffer, as_attachment=True, filename=f"receipt_{payment.receipt_number}.pdf")


@student_required
def receipt_view(request, payment_id):
    payment = get_object_or_404(Payment, pk=payment_id, student=request.user)
    return render(request, "payments/receipt.html", {"payment": payment})


@csrf_exempt
@require_POST
def mpesa_callback(request):
    """M-Pesa STK Push callback — auto-approve or mark failed server-side."""
    try:
        body = json.loads(request.body)
        result = body.get("Body", {}).get("stkCallback", {})
        checkout_id = result.get("CheckoutRequestID")
        result_code = result.get("ResultCode")

        payment = Payment.objects.filter(
            checkout_request_id=checkout_id, status=Payment.Status.PENDING
        ).first()
        if not payment:
            return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

        if result_code == 0:
            mpesa_ref = ""
            for item in result.get("CallbackMetadata", {}).get("Item", []):
                if item.get("Name") == "MpesaReceiptNumber":
                    mpesa_ref = str(item.get("Value", ""))
            if mpesa_ref:
                payment.transaction_id = mpesa_ref
                payment.save(update_fields=["transaction_id"])
            payment.approve()
            log_audit(request, "mpesa_callback_success", "Payment", payment.pk)
        else:
            desc = result.get("ResultDesc", "Payment was not completed.")
            payment.mark_failed(desc)
            log_audit(request, "mpesa_callback_failed", "Payment", payment.pk, desc)

        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
    except Exception as exc:
        logger.exception("M-Pesa callback error: %s", exc)
        return JsonResponse({"ResultCode": 1, "ResultDesc": "Error"}, status=400)
