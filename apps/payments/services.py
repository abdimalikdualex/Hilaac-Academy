import base64
import io
import logging
from datetime import datetime, timedelta

import requests
from django.conf import settings
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

from .constants import PAYMENT_METHOD_META, PAYMENT_SUCCESS_MESSAGE, PUSH_PAYMENT_METHODS
from .models import Payment

logger = logging.getLogger(__name__)


def mpesa_configured():
    return all(
        [
            settings.MPESA_CONSUMER_KEY,
            settings.MPESA_CONSUMER_SECRET,
            settings.MPESA_SHORTCODE,
            settings.MPESA_PASSKEY,
            settings.MPESA_CALLBACK_URL,
        ]
    )


def mpesa_base_url():
    env = getattr(settings, "MPESA_ENV", "sandbox")
    if env == "production":
        return "https://api.safaricom.co.ke"
    return "https://sandbox.safaricom.co.ke"


def normalize_phone(phone, method):
    """Normalize and validate phone for the selected wallet."""
    raw = phone.strip().lstrip("+")
    if not raw.isdigit():
        return None, "Phone number must contain digits only."

    if method == Payment.Method.MPESA:
        if raw.startswith("254"):
            normalized = raw
        elif raw.startswith("0"):
            normalized = "254" + raw[1:]
        elif raw.startswith("7") and len(raw) == 9:
            normalized = "254" + raw
        else:
            return None, "Kenya M-Pesa: use 2547XXXXXXXX or 07XXXXXXXX."
        if len(normalized) != 12 or not normalized.startswith("2547"):
            return None, "Kenya M-Pesa: use 2547XXXXXXXX."
        return normalized, None

    if method in (Payment.Method.EVC_PLUS, Payment.Method.SAHAL):
        if raw.startswith("252"):
            normalized = raw
        elif raw.startswith("61"):
            normalized = "252" + raw
        elif len(raw) >= 9:
            normalized = "252" + raw if not raw.startswith("252") else raw
        else:
            return None, "Somalia: use 61XXXXXXXX or 25261XXXXXXX."
        return normalized, None

    if method == Payment.Method.ZAAD:
        if raw.startswith("252"):
            normalized = raw
        elif raw.startswith("63"):
            normalized = "252" + raw
        else:
            return None, "Somaliland Zaad: use 63XXXXXXXX or 25263XXXXXXX."
        return normalized, None

    return raw, None


def get_mpesa_access_token():
    if not mpesa_configured():
        return None
    auth = base64.b64encode(
        f"{settings.MPESA_CONSUMER_KEY}:{settings.MPESA_CONSUMER_SECRET}".encode()
    ).decode()
    url = f"{mpesa_base_url()}/oauth/v1/generate?grant_type=client_credentials"
    resp = requests.get(url, headers={"Authorization": f"Basic {auth}"}, timeout=30)
    if resp.ok:
        return resp.json().get("access_token")
    logger.warning("M-Pesa token error: %s", resp.text)
    return None


def initiate_mpesa_stk_push(phone, amount, account_ref, description):
    """Initiate M-Pesa STK Push. Returns (success, message, checkout_request_id)."""
    token = get_mpesa_access_token()
    if not token:
        return False, "M-Pesa is not configured.", None

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password_str = f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}"
    password = base64.b64encode(password_str.encode()).decode()

    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": settings.MPESA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": settings.MPESA_CALLBACK_URL,
        "AccountReference": account_ref[:12],
        "TransactionDesc": description[:13],
    }
    url = f"{mpesa_base_url()}/mpesa/stkpush/v1/processrequest"
    resp = requests.post(
        url,
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    data = resp.json()
    if resp.ok and data.get("ResponseCode") == "0":
        return True, data.get("CustomerMessage", "STK Push sent to your phone."), data.get("CheckoutRequestID")
    err = data.get("errorMessage") or data.get("ResponseDescription") or "STK Push failed."
    return False, err, None


def query_mpesa_stk_status(checkout_request_id):
    """Query STK transaction status. Returns (result_code, description, receipt)."""
    token = get_mpesa_access_token()
    if not token or not checkout_request_id:
        return None, "", ""

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password_str = f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}"
    password = base64.b64encode(password_str.encode()).decode()
    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_request_id,
    }
    url = f"{mpesa_base_url()}/mpesa/stkpushquery/v1/query"
    resp = requests.post(
        url,
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if not resp.ok:
        return None, "", ""
    data = resp.json()
    code = data.get("ResultCode")
    if code is None:
        return None, data.get("ResponseDescription", ""), ""
    if str(code) == "0":
        return 0, "Payment successful.", data.get("MpesaReceiptNumber", "")
    return int(code), data.get("ResultDesc", "Payment failed."), ""


def initiate_evc_plus_push(phone, amount, reference):
    """EVC Plus push — calls provider API when configured, else dev simulation."""
    if settings.EVC_PLUS_MERCHANT_ID and settings.EVC_PLUS_API_KEY:
        # Placeholder for live Hormuud merchant API integration
        api_url = getattr(settings, "EVC_PLUS_API_URL", "")
        if api_url:
            try:
                resp = requests.post(
                    api_url,
                    json={
                        "merchant_id": settings.EVC_PLUS_MERCHANT_ID,
                        "phone": phone,
                        "amount": str(amount),
                        "reference": reference,
                    },
                    headers={"Authorization": f"Bearer {settings.EVC_PLUS_API_KEY}"},
                    timeout=30,
                )
                if resp.ok:
                    data = resp.json()
                    return True, data.get("message", "EVC Plus push sent."), data.get("checkout_id", f"EVC-{reference}")
            except Exception as exc:
                logger.exception("EVC Plus API error: %s", exc)
                return False, "Could not reach EVC Plus. Try again.", None
    if settings.DEBUG:
        return True, PAYMENT_METHOD_META["evc_plus"]["pin_message"], f"DEV-EVC-{reference}"
    return False, "EVC Plus instant payment is not configured yet.", None


def initiate_zaad_push(phone, amount, reference):
    if getattr(settings, "ZAAD_API_KEY", "") and getattr(settings, "ZAAD_MERCHANT_ID", ""):
        api_url = getattr(settings, "ZAAD_API_URL", "")
        if api_url:
            try:
                resp = requests.post(
                    api_url,
                    json={"phone": phone, "amount": str(amount), "reference": reference},
                    headers={"X-API-Key": settings.ZAAD_API_KEY},
                    timeout=30,
                )
                if resp.ok:
                    data = resp.json()
                    return True, data.get("message", "Zaad push sent."), data.get("checkout_id", f"ZAAD-{reference}")
            except Exception as exc:
                logger.exception("Zaad API error: %s", exc)
    if settings.DEBUG:
        return True, PAYMENT_METHOD_META["zaad"]["pin_message"], f"DEV-ZAAD-{reference}"
    return False, "Zaad instant payment is not configured yet.", None


def initiate_sahal_push(phone, amount, reference):
    if getattr(settings, "SAHAL_API_KEY", "") and getattr(settings, "SAHAL_MERCHANT_ID", ""):
        api_url = getattr(settings, "SAHAL_API_URL", "")
        if api_url:
            try:
                resp = requests.post(
                    api_url,
                    json={"phone": phone, "amount": str(amount), "reference": reference},
                    headers={"Authorization": f"Bearer {settings.SAHAL_API_KEY}"},
                    timeout=30,
                )
                if resp.ok:
                    data = resp.json()
                    return True, data.get("message", "Sahal push sent."), data.get("checkout_id", f"SAHAL-{reference}")
            except Exception as exc:
                logger.exception("Sahal API error: %s", exc)
    if settings.DEBUG:
        return True, PAYMENT_METHOD_META["sahal"]["pin_message"], f"DEV-SAHAL-{reference}"
    return False, "Sahal instant payment is not configured yet.", None


def initiate_push_payment(payment):
    """Send wallet push for a pending payment. Updates payment fields."""
    method = payment.method
    phone = payment.phone_number
    amount = payment.amount
    ref = payment.receipt_number
    desc = f"Hilaac {payment.level.name}"

    dispatch = {
        Payment.Method.MPESA: initiate_mpesa_stk_push,
        Payment.Method.EVC_PLUS: lambda p, a, r, d: initiate_evc_plus_push(p, a, r),
        Payment.Method.ZAAD: lambda p, a, r, d: initiate_zaad_push(p, a, r),
        Payment.Method.SAHAL: lambda p, a, r, d: initiate_sahal_push(p, a, r),
    }
    fn = dispatch.get(method)
    if not fn:
        return False, "Unsupported payment method.", None

    if method == Payment.Method.MPESA and not mpesa_configured() and settings.DEBUG:
        checkout_id = f"DEV-MPESA-{payment.pk or ref}"
        msg = PAYMENT_METHOD_META["mpesa"]["pin_message"]
        payment.checkout_request_id = checkout_id
        payment.provider_message = msg
        payment.save(update_fields=["checkout_request_id", "provider_message"])
        return True, msg, checkout_id

    success, message, checkout_id = fn(phone, amount, ref, desc)
    if checkout_id:
        payment.checkout_request_id = checkout_id
    payment.provider_message = message
    payment.save(update_fields=["checkout_request_id", "provider_message"])
    return success, message, checkout_id


def _dev_simulation_complete(payment):
    """In DEBUG, auto-complete simulated push payments after a short delay."""
    if not settings.DEBUG:
        return False
    if not payment.checkout_request_id or not payment.checkout_request_id.startswith("DEV-"):
        return False
    age = timezone.now() - payment.created_at
    return age >= timedelta(seconds=6)


def verify_payment_status(payment):
    """
    Poll provider for payment status. Returns dict:
    {status, message, transaction_id, redirect_url}
    """
    from django.urls import reverse

    course_url = reverse("learning:course_view", kwargs={"level_id": payment.level_id})

    if payment.status == Payment.Status.COMPLETED:
        return {
            "status": "completed",
            "message": PAYMENT_SUCCESS_MESSAGE,
            "redirect_url": course_url,
        }
    if payment.status in (Payment.Status.FAILED, Payment.Status.CANCELLED, Payment.Status.REJECTED):
        return {
            "status": payment.status,
            "message": payment.failure_message or "Payment was not completed.",
            "redirect_url": reverse("payments:checkout", kwargs={"level_id": payment.level_id}),
        }

    if payment.method == Payment.Method.MPESA and payment.checkout_request_id:
        if payment.checkout_request_id.startswith("DEV-"):
            if _dev_simulation_complete(payment):
                payment.transaction_id = f"SIM{payment.pk}"
                payment.save(update_fields=["transaction_id"])
                payment.approve()
                return {
                    "status": "completed",
                    "message": PAYMENT_SUCCESS_MESSAGE,
                    "redirect_url": course_url,
                }
        else:
            code, desc, receipt = query_mpesa_stk_status(payment.checkout_request_id)
            if code == 0:
                if receipt:
                    payment.transaction_id = receipt
                    payment.save(update_fields=["transaction_id"])
                payment.approve()
                return {
                    "status": "completed",
                    "message": PAYMENT_SUCCESS_MESSAGE,
                    "redirect_url": course_url,
                }
            if code is not None and code != 0:
                payment.mark_failed(desc or "Payment was not completed.")
                return {
                    "status": "failed",
                    "message": desc or "Payment was not completed.",
                    "redirect_url": reverse("payments:checkout", kwargs={"level_id": payment.level_id}),
                }

    if payment.method in PUSH_PAYMENT_METHODS and payment.checkout_request_id:
        if payment.checkout_request_id.startswith("DEV-") and _dev_simulation_complete(payment):
            payment.transaction_id = f"SIM{payment.pk}"
            payment.save(update_fields=["transaction_id"])
            payment.approve()
            return {
                "status": "completed",
                "message": PAYMENT_SUCCESS_MESSAGE,
                "redirect_url": course_url,
            }

    # Timeout after 3 minutes
    if timezone.now() - payment.created_at > timedelta(minutes=3):
        payment.mark_failed("Payment timed out. Please try again.")
        return {
            "status": "failed",
            "message": "Payment timed out. Please try again.",
            "redirect_url": reverse("payments:checkout", kwargs={"level_id": payment.level_id}),
        }

    return {
        "status": "pending",
        "message": "Waiting for payment confirmation...",
        "redirect_url": "",
    }


def generate_receipt_pdf(payment):
    from apps.payments.currency import format_amount, format_payment_display

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width / 2, height - 3 * cm, "Hilaac Academy")
    c.setFont("Helvetica", 14)
    c.drawCentredString(width / 2, height - 4 * cm, "Payment Receipt")

    y = height - 6 * cm
    txn = payment.transaction_id or payment.reference or "N/A"
    lines = [
        f"Receipt No: {payment.receipt_number}",
        f"Date: {payment.verified_at or payment.created_at:%B %d, %Y %H:%M}",
        f"Student: {payment.student.get_full_name() or payment.student.username}",
        f"Email: {payment.student.email}",
        f"Course: {payment.level.language.name} - {payment.level.name}",
        f"Amount Paid: {format_payment_display(payment)}",
        f"Base Price: {format_amount(payment.amount_usd or payment.amount, 'USD')}",
        f"Payment Method: {payment.get_method_display()}",
        f"Transaction ID: {txn}",
        f"Phone: {payment.phone_number}",
        f"Status: {payment.get_status_display()}",
    ]
    c.setFont("Helvetica", 12)
    for line in lines:
        c.drawString(3 * cm, y, line)
        y -= 0.8 * cm

    c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(width / 2, 3 * cm, "Thank you for learning with Hilaac Academy!")
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer
