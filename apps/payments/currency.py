"""Multi-currency pricing, display, and checkout charge logic."""
from decimal import Decimal, ROUND_HALF_UP

from django.core.cache import cache

BASE_CURRENCY = "USD"

DEFAULT_RATES = {
    "KES": Decimal("129.0000"),
    "SOS": Decimal("570.0000"),
    "SLSH": Decimal("570.0000"),
    "ETB": Decimal("56.0000"),
}

# Payment providers charge in these currencies.
METHOD_CHARGE_CURRENCY = {
    "mpesa": "KES",
    "evc_plus": "USD",
    "zaad": "USD",
    "sahal": "USD",
    "bank_transfer": None,
}

COUNTRY_DISPLAY_CURRENCY = {
    "KE": "KES",
    "US": "USD",
    "SO": "USD",
}


def _normalize_country(value):
    return (value or "").strip().lower()


def _country_from_profile(user):
    if not user or not getattr(user, "is_authenticated", False) or not user.is_authenticated:
        return None
    country = _normalize_country(getattr(user, "country", ""))
    if not country:
        return None
    if "kenya" in country or country in {"ke", "ken"}:
        return "KE"
    if "somalia" in country or country in {"so", "som"}:
        return "SO"
    if "united states" in country or country in {"us", "usa", "united states of america"}:
        return "US"
    if "ethiopia" in country or country in {"et", "eth"}:
        return "ET"
    if "somaliland" in country:
        return "SO"
    return None


def _country_from_request(request):
    if not request:
        return None
    cf = (request.META.get("HTTP_CF_IPCOUNTRY") or "").upper()
    if cf and cf not in {"XX", "T1"}:
        return cf
    accept = request.META.get("HTTP_ACCEPT_LANGUAGE", "")
    for part in accept.split(","):
        token = part.split(";")[0].strip()
        if "-" in token:
            region = token.split("-")[-1].upper()
            if len(region) == 2:
                return region
    return None


def detect_country_code(request=None, user=None):
    return (
        _country_from_profile(user)
        or _country_from_request(request)
        or "US"
    )


def get_display_currency(country_code=None):
    if not country_code:
        return BASE_CURRENCY
    return COUNTRY_DISPLAY_CURRENCY.get(country_code.upper(), BASE_CURRENCY)


def get_exchange_rate(to_currency):
    if to_currency == BASE_CURRENCY:
        return Decimal("1.0000")
    cache_key = f"fx:USD:{to_currency}"
    cached = cache.get(cache_key)
    if cached is not None:
        return Decimal(str(cached))

    from apps.payments.models import ExchangeRate

    rate_obj = (
        ExchangeRate.objects.filter(from_currency=BASE_CURRENCY, to_currency=to_currency, is_active=True)
        .order_by("-updated_at")
        .first()
    )
    rate = rate_obj.rate if rate_obj else DEFAULT_RATES.get(to_currency, Decimal("1.0000"))
    cache.set(cache_key, str(rate), 300)
    return rate


def convert_usd(amount_usd, to_currency):
    amount_usd = Decimal(str(amount_usd or 0))
    if to_currency == BASE_CURRENCY:
        return amount_usd.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    converted = amount_usd * get_exchange_rate(to_currency)
    if to_currency == "KES":
        return converted.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return converted.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def format_amount(amount, currency):
    amount = Decimal(str(amount or 0))
    if currency == "KES":
        return f"KSh {amount:,.0f}"
    if currency == BASE_CURRENCY:
        return f"${amount:,.2f} USD"
    return f"{amount:,.2f} {currency}"


def get_charge_currency(method, country_code=None):
    method = (method or "").lower()
    mapped = METHOD_CHARGE_CURRENCY.get(method)
    if mapped:
        return mapped
    if method == "bank_transfer":
        return "KES" if country_code == "KE" else BASE_CURRENCY
    return BASE_CURRENCY


def get_pricing(request, level, method=None):
    user = getattr(request, "user", None) if request else None
    country_code = detect_country_code(request, user)
    display_currency = get_display_currency(country_code)

    if getattr(level, "is_free", False):
        zero = Decimal("0")
        return {
            "is_free": True,
            "amount_usd": zero,
            "display_currency": display_currency,
            "display_amount": zero,
            "primary_formatted": "Free",
            "usd_formatted": "Free",
            "dual_formatted": "Free",
            "show_dual": False,
            "charge_currency": BASE_CURRENCY,
            "charge_amount": zero,
            "charge_formatted": "Free",
            "exchange_rate": get_exchange_rate(display_currency),
            "country_code": country_code,
        }

    amount_usd = Decimal(str(level.price))
    display_amount = convert_usd(amount_usd, display_currency)
    charge_currency = get_charge_currency(method, country_code) if method else display_currency
    charge_amount = convert_usd(amount_usd, charge_currency)
    usd_formatted = format_amount(amount_usd, BASE_CURRENCY)
    primary_formatted = format_amount(display_amount, display_currency)

    return {
        "is_free": False,
        "amount_usd": amount_usd,
        "display_currency": display_currency,
        "display_amount": display_amount,
        "primary_formatted": primary_formatted,
        "usd_formatted": usd_formatted,
        "dual_formatted": f"{primary_formatted} ({usd_formatted})" if display_currency != BASE_CURRENCY else usd_formatted,
        "show_dual": display_currency != BASE_CURRENCY,
        "charge_currency": charge_currency,
        "charge_amount": charge_amount,
        "charge_formatted": format_amount(charge_amount, charge_currency),
        "exchange_rate": get_exchange_rate(charge_currency) if charge_currency != BASE_CURRENCY else Decimal("1.0000"),
        "country_code": country_code,
    }


def build_payment_amounts(request, level, method):
    pricing = get_pricing(request, level, method)
    return {
        "amount": pricing["charge_amount"],
        "amount_usd": pricing["amount_usd"],
        "currency": pricing["charge_currency"],
        "exchange_rate": pricing["exchange_rate"],
    }


def get_checkout_methods_pricing(request, level):
    from apps.payments.constants import PAYMENT_METHOD_META

    payload = {}
    for key in PAYMENT_METHOD_META:
        p = get_pricing(request, level, key)
        payload[key] = {
            "charge_formatted": p["charge_formatted"],
            "charge_amount": str(p["charge_amount"]),
            "charge_currency": p["charge_currency"],
            "usd_formatted": p["usd_formatted"],
            "dual_formatted": p["dual_formatted"],
            "display_formatted": p["dual_formatted"] if p["show_dual"] else p["usd_formatted"],
        }
    return payload


def format_payment_display(payment):
    if payment.currency == "KES":
        local = format_amount(payment.amount, "KES")
    else:
        local = format_amount(payment.amount, payment.currency)
    usd = format_amount(payment.amount_usd or payment.amount, BASE_CURRENCY)
    if payment.currency != BASE_CURRENCY:
        return f"{local} ({usd})"
    return usd


def revenue_totals(queryset):
    """Return USD base total and KES collected total for completed payments."""
    usd_total = Decimal("0")
    kes_collected = Decimal("0")
    usd_collected = Decimal("0")
    for payment in queryset.only("amount", "amount_usd", "currency", "status"):
        if payment.status != payment.Status.COMPLETED:
            continue
        base = payment.amount_usd if payment.amount_usd is not None else payment.amount
        usd_total += Decimal(str(base))
        if payment.currency == "KES":
            kes_collected += Decimal(str(payment.amount))
        elif payment.currency == BASE_CURRENCY:
            usd_collected += Decimal(str(payment.amount))
    kes_equivalent = convert_usd(usd_total, "KES")
    return {
        "total_usd": usd_total.quantize(Decimal("0.01")),
        "total_kes_collected": kes_collected.quantize(Decimal("1")),
        "total_usd_collected": usd_collected.quantize(Decimal("0.01")),
        "total_kes_equivalent": kes_equivalent,
        "usd_formatted": format_amount(usd_total, BASE_CURRENCY),
        "kes_formatted": format_amount(kes_equivalent, "KES"),
    }
