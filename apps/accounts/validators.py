import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class HilaacPasswordValidator:
    """Require 8+ chars with upper, lower, digit, and special character."""

    def validate(self, password, user=None):
        if len(password) < 8:
            raise ValidationError(_("Password must be at least 8 characters."), code="password_too_short")
        if not re.search(r"[A-Z]", password):
            raise ValidationError(_("Password must include an uppercase letter."), code="password_no_upper")
        if not re.search(r"[a-z]", password):
            raise ValidationError(_("Password must include a lowercase letter."), code="password_no_lower")
        if not re.search(r"\d", password):
            raise ValidationError(_("Password must include a number."), code="password_no_digit")
        if not re.search(r"[^A-Za-z0-9]", password):
            raise ValidationError(_("Password must include a special character."), code="password_no_special")

    def get_help_text(self):
        return (
            "At least 8 characters with uppercase, lowercase, a number, and a special character."
        )
