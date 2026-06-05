from django.conf import settings
from django.template.loader import render_to_string


def render_branded_email(template_name, context=None):
    context = context or {}
    context.setdefault("site_url", settings.SITE_URL.rstrip("/"))
    context.setdefault("whatsapp_number", settings.WHATSAPP_SUPPORT_NUMBER)
    html = render_to_string(template_name, context)
    text = render_to_string(template_name.replace(".html", ".txt"), context)
    return text.strip(), html


def branded_subject(label):
    return f"Hilaac Academy — {label}"
