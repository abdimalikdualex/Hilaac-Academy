from django.utils.translation import gettext_lazy as _

PUSH_PAYMENT_METHODS = ("mpesa", "evc_plus", "zaad", "sahal")

PAYMENT_SUCCESS_MESSAGE = _("Payment successful. You can now access this course.")

PAYMENT_METHOD_META = {
    "mpesa": {
        "label": "M-Pesa",
        "region": "Kenya",
        "phone_hint": "2547XXXXXXXX",
        "phone_example": "254712345678",
        "pin_message": "Enter your M-Pesa PIN to complete payment.",
        "logo": "mpesa",
    },
    "evc_plus": {
        "label": "EVC Plus",
        "region": "Somalia",
        "phone_hint": "61XXXXXXXX or 25261XXXXXXX",
        "phone_example": "615551234",
        "pin_message": "Fadlan geli PIN-kaaga si aad u xaqiijiso lacag bixinta.",
        "logo": "evc_plus",
    },
    "zaad": {
        "label": "Zaad",
        "region": "Somaliland",
        "phone_hint": "63XXXXXXXX or 25263XXXXXXX",
        "phone_example": "634567890",
        "pin_message": "Fadlan xaqiiji lacag bixinta.",
        "logo": "zaad",
    },
    "sahal": {
        "label": "Sahal",
        "region": "Somalia",
        "phone_hint": "61XXXXXXXX or 25261XXXXXXX",
        "phone_example": "615559876",
        "pin_message": "Fadlan xaqiiji lacag bixinta Sahal.",
        "logo": "sahal",
    },
}

# Legacy manual instructions (admin fallback)
PAYMENT_METHOD_INSTRUCTIONS = {
    key: {
        "label": meta["label"],
        "instructions": [meta["pin_message"]],
    }
    for key, meta in PAYMENT_METHOD_META.items()
}
