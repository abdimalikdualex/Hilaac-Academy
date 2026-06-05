import re

from django import forms

from .constants import PAYMENT_METHOD_META, PUSH_PAYMENT_METHODS
from .models import Payment

_INPUT = "w-full px-4 py-3 rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-lg"


class InstantPaymentForm(forms.Form):
    """One-click push payment — phone + method only (no manual reference)."""

    method = forms.ChoiceField(
        choices=[(m, PAYMENT_METHOD_META[m]["label"]) for m in PUSH_PAYMENT_METHODS],
        widget=forms.RadioSelect(attrs={"class": "sr-only"}),
    )
    phone_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": _INPUT,
                "placeholder": "Phone number",
                "inputmode": "tel",
                "autocomplete": "tel",
            }
        ),
    )

    def clean_phone_number(self):
        phone = re.sub(r"[\s\-()]+", "", self.cleaned_data.get("phone_number", ""))
        if not phone:
            raise forms.ValidationError("Phone number is required.")
        if not re.match(r"^\+?\d{9,15}$", phone):
            raise forms.ValidationError("Enter a valid phone number (digits only).")
        return phone

    def clean(self):
        cleaned = super().clean()
        method = cleaned.get("method")
        phone = cleaned.get("phone_number")
        if method and phone:
            from .services import normalize_phone

            normalized, error = normalize_phone(phone, method)
            if error:
                self.add_error("phone_number", error)
            else:
                cleaned["phone_number"] = normalized
        return cleaned


class PaymentSubmissionForm(forms.ModelForm):
    """Legacy manual submission (admin fallback)."""

    class Meta:
        model = Payment
        fields = ("method", "reference", "phone_number", "screenshot")
        widgets = {
            "method": forms.Select(attrs={"class": _INPUT}),
            "reference": forms.TextInput(attrs={"class": _INPUT}),
            "phone_number": forms.TextInput(attrs={"class": _INPUT}),
            "screenshot": forms.FileInput(attrs={"class": "w-full text-sm", "accept": "image/*"}),
        }
