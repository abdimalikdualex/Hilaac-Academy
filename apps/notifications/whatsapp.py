"""WhatsApp notification delivery (webhook or log fallback)."""
import logging
import re

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def normalize_phone(phone: str) -> str:
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("0") and len(digits) >= 10:
        digits = "254" + digits[1:]
    if not digits.startswith("+"):
        digits = "+" + digits if digits else ""
    return digits if digits.startswith("+") else f"+{digits}"


def whatsapp_deep_link(phone: str, message: str) -> str:
    num = normalize_phone(phone).replace("+", "")
    from urllib.parse import quote

    return f"https://wa.me/{num}?text={quote(message)}"


def send_whatsapp_message(phone: str, message: str) -> bool:
    """
    Send via configured webhook (VPS can point to Twilio, Meta Cloud API proxy, etc.).
    Returns True when the webhook accepts the message.
    """
    if not getattr(settings, "WHATSAPP_AUTO_NOTIFY", True):
        return False
    phone = normalize_phone(phone)
    if not phone or not message:
        return False

    webhook = getattr(settings, "WHATSAPP_NOTIFY_WEBHOOK_URL", "") or ""
    if webhook:
        try:
            resp = requests.post(
                webhook,
                json={"phone": phone, "message": message},
                headers={"Authorization": f"Bearer {getattr(settings, 'WHATSAPP_NOTIFY_TOKEN', '')}"},
                timeout=12,
            )
            if resp.ok:
                return True
            logger.warning("WhatsApp webhook returned %s: %s", resp.status_code, resp.text[:200])
        except requests.RequestException:
            logger.exception("WhatsApp webhook failed for %s", phone)

    logger.info("WhatsApp (log only) → %s: %s", phone, message[:120])
    return False


def notify_student_whatsapp(student, message: str) -> bool:
    phone = getattr(student, "phone", "") or ""
    return send_whatsapp_message(phone, message)
