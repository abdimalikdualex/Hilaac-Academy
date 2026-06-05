from django import template

from apps.payments.currency import format_payment_display, get_pricing

register = template.Library()


@register.inclusion_tag("partials/price_display.html", takes_context=True)
def price_display(context, level, size="md", show_usd_equiv=False):
    request = context.get("request")
    pricing = get_pricing(request, level)
    return {
        "level": level,
        "pricing": pricing,
        "size": size,
        "show_usd_equiv": show_usd_equiv or pricing.get("show_dual"),
    }


@register.simple_tag
def payment_amount_display(payment):
    return format_payment_display(payment)


@register.simple_tag(takes_context=True)
def course_price(context, level):
    return get_pricing(context.get("request"), level)
