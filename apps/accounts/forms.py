from django import forms
from django.conf import settings
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from apps.core.imaging import ALLOWED_IMAGE_EXTS

from .models import User

PROFILE_PHOTO_MAX_BYTES = 5 * 1024 * 1024
PASSWORD_INPUT_CLASS = (
    "password-field-input w-full px-4 py-3 pr-12 rounded-lg border border-slate-300 outline-none "
    "focus:ring-2 focus:ring-[#1E4D8F] text-[#0B1736] bg-white text-base"
)


class HilaacPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field_config = {
            "old_password": {
                "label": _("Current Password"),
                "placeholder": _("Enter your current password"),
            },
            "new_password1": {
                "label": _("New Password"),
                "placeholder": _("Create a new password"),
            },
            "new_password2": {
                "label": _("Confirm New Password"),
                "placeholder": _("Confirm your new password"),
            },
        }
        for name, config in field_config.items():
            field = self.fields[name]
            field.label = config["label"]
            field.widget.attrs.setdefault("class", PASSWORD_INPUT_CLASS)
            field.widget.attrs.setdefault("placeholder", config["placeholder"])
            field.widget.attrs.setdefault("autocomplete", "off")
        self.fields["new_password1"].help_text = ""

    def clean_old_password(self):
        old_password = self.cleaned_data.get("old_password")
        if old_password and not self.user.check_password(old_password):
            raise forms.ValidationError(_("Current password is incorrect."))
        return old_password

    def clean_new_password2(self):
        password1 = self.cleaned_data.get("new_password1")
        password2 = self.cleaned_data.get("new_password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(_("Passwords do not match."))
        return super().clean_new_password2()

    def clean_new_password1(self):
        password = self.cleaned_data.get("new_password1")
        if not password:
            return password
        errors = []
        if len(password) < 8:
            errors.append(_("Password does not meet requirements."))
        if not any(c.isupper() for c in password):
            errors.append(_("Password does not meet requirements."))
        if not any(c.islower() for c in password):
            errors.append(_("Password does not meet requirements."))
        if not any(c.isdigit() for c in password):
            errors.append(_("Password does not meet requirements."))
        if not any(not c.isalnum() for c in password):
            errors.append(_("Password does not meet requirements."))
        if errors:
            raise forms.ValidationError(errors[0])
        password_validation.validate_password(password, self.user)
        return password


class HilaacAuthenticationForm(AuthenticationForm):
    """Strip accidental whitespace; email can be typed in the username field."""

    error_messages = {
        "invalid_login": _("Invalid username or password."),
        "inactive": _("This account is deactivated. Contact support."),
    }

    def clean_username(self):
        return (self.cleaned_data.get("username") or "").strip()

    def clean_password(self):
        return (self.cleaned_data.get("password") or "").strip()


class StudentRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, label=_("Email"))
    first_name = forms.CharField(max_length=150, required=True, label=_("First Name"))
    last_name = forms.CharField(max_length=150, required=True, label=_("Last Name"))
    phone = forms.CharField(max_length=20, required=False, label=_("Phone"))
    country = forms.CharField(max_length=100, required=False, label=_("Country"))

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "phone", "country", "password1", "password2")
        labels = {
            "username": _("Username"),
            "password1": _("Password"),
            "password2": _("Confirm Password"),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.role = User.Role.STUDENT
        if not settings.REQUIRE_EMAIL_VERIFICATION:
            user.is_verified = True
        if commit:
            user.save()
        return user


def _validate_profile_photo(uploaded):
    if not uploaded:
        return uploaded
    ext = "." + uploaded.name.rsplit(".", 1)[-1].lower() if "." in uploaded.name else ""
    if ext not in ALLOWED_IMAGE_EXTS:
        raise forms.ValidationError(_("Use JPG, PNG, or WebP images only."))
    if uploaded.size > PROFILE_PHOTO_MAX_BYTES:
        raise forms.ValidationError(_("Profile photo must be 5 MB or smaller."))
    return uploaded


class BaseProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
            "phone",
            "country",
            "city",
            "gender",
            "date_of_birth",
            "profile_photo",
        )
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "profile-input"}),
            "last_name": forms.TextInput(attrs={"class": "profile-input"}),
            "email": forms.EmailInput(attrs={"class": "profile-input"}),
            "phone": forms.TextInput(attrs={"class": "profile-input"}),
            "country": forms.TextInput(attrs={"class": "profile-input"}),
            "city": forms.TextInput(attrs={"class": "profile-input"}),
            "gender": forms.Select(attrs={"class": "profile-input"}),
            "date_of_birth": forms.DateInput(attrs={"class": "profile-input", "type": "date"}),
        }

    def clean_profile_photo(self):
        return _validate_profile_photo(self.cleaned_data.get("profile_photo"))


class StudentProfileForm(BaseProfileForm):
    class Meta(BaseProfileForm.Meta):
        fields = BaseProfileForm.Meta.fields + ("language_preference",)
        widgets = {
            **BaseProfileForm.Meta.widgets,
            "language_preference": forms.Select(attrs={"class": "profile-input"}),
        }


class InstructorProfileForm(BaseProfileForm):
    class Meta(BaseProfileForm.Meta):
        fields = BaseProfileForm.Meta.fields + (
            "bio",
            "teaching_experience",
            "specialization",
            "skills",
            "certifications",
            "linkedin_url",
            "website_url",
        )
        widgets = {
            **BaseProfileForm.Meta.widgets,
            "bio": forms.Textarea(attrs={"class": "profile-input", "rows": 4}),
            "teaching_experience": forms.Textarea(attrs={"class": "profile-input", "rows": 3}),
            "specialization": forms.TextInput(attrs={"class": "profile-input"}),
            "skills": forms.TextInput(attrs={"class": "profile-input", "placeholder": "e.g. English, ICT, Curriculum Design"}),
            "certifications": forms.Textarea(attrs={"class": "profile-input", "rows": 2}),
            "linkedin_url": forms.URLInput(attrs={"class": "profile-input", "placeholder": "https://linkedin.com/in/..."}),
            "website_url": forms.URLInput(attrs={"class": "profile-input", "placeholder": "https://"}),
        }


class AdminProfileForm(BaseProfileForm):
    """Super Admin personal profile — no instructor-only fields."""


SETTINGS_INPUT_CLASS = (
    "w-full px-4 py-3 rounded-lg border border-slate-300 bg-white text-[#0B1736] "
    "placeholder:text-slate-400 focus:ring-2 focus:ring-[#1E4D8F] outline-none"
)


class SettingsProfileForm(forms.ModelForm):
    """Simplified settings profile — photo, name, phone, and optional bio."""

    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone", "bio", "profile_photo")
        widgets = {
            "first_name": forms.TextInput(attrs={"class": SETTINGS_INPUT_CLASS, "placeholder": "First name"}),
            "last_name": forms.TextInput(attrs={"class": SETTINGS_INPUT_CLASS, "placeholder": "Last name"}),
            "phone": forms.TextInput(attrs={"class": SETTINGS_INPUT_CLASS, "placeholder": "Phone number"}),
            "bio": forms.Textarea(
                attrs={"class": SETTINGS_INPUT_CLASS, "rows": 3, "placeholder": "Short bio (optional)"}
            ),
        }

    def clean_profile_photo(self):
        return _validate_profile_photo(self.cleaned_data.get("profile_photo"))


class InstructorSettingsProfileForm(SettingsProfileForm):
    class Meta(SettingsProfileForm.Meta):
        fields = SettingsProfileForm.Meta.fields + ("bio",)
        widgets = {
            **SettingsProfileForm.Meta.widgets,
            "bio": forms.Textarea(attrs={"class": SETTINGS_INPUT_CLASS, "rows": 3, "placeholder": "Short bio"}),
        }


class AccountSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("email", "phone", "city")
        widgets = {
            "email": forms.EmailInput(attrs={"class": "profile-input"}),
            "phone": forms.TextInput(attrs={"class": "profile-input"}),
            "city": forms.TextInput(attrs={"class": "profile-input"}),
        }


class NotificationPreferencesForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            "notify_course_updates",
            "notify_assignments",
            "notify_certificates",
            "notify_marketing",
            "notify_system",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        labels = {
            "notify_course_updates": _("Course updates"),
            "notify_assignments": _("Assignment notifications"),
            "notify_certificates": _("Certificate notifications"),
            "notify_marketing": _("Marketing emails"),
            "notify_system": _("System announcements"),
        }
        for field in self.fields:
            self.fields[field].widget.attrs["class"] = "rounded"
            if field in labels:
                self.fields[field].label = labels[field]


# Legacy alias used by older views
ProfileForm = StudentProfileForm
