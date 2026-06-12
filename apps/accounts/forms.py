from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm

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
                "label": "Current Password",
                "placeholder": "Enter your current password",
            },
            "new_password1": {
                "label": "New Password",
                "placeholder": "Create a new password",
            },
            "new_password2": {
                "label": "Confirm New Password",
                "placeholder": "Confirm your new password",
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
            raise forms.ValidationError("Current password is incorrect.")
        return old_password

    def clean_new_password2(self):
        password1 = self.cleaned_data.get("new_password1")
        password2 = self.cleaned_data.get("new_password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        return super().clean_new_password2()

    def clean_new_password1(self):
        password = self.cleaned_data.get("new_password1")
        if not password:
            return password
        errors = []
        if len(password) < 8:
            errors.append("Password does not meet requirements.")
        if not any(c.isupper() for c in password):
            errors.append("Password does not meet requirements.")
        if not any(c.islower() for c in password):
            errors.append("Password does not meet requirements.")
        if not any(c.isdigit() for c in password):
            errors.append("Password does not meet requirements.")
        if not any(not c.isalnum() for c in password):
            errors.append("Password does not meet requirements.")
        if errors:
            raise forms.ValidationError(errors[0])
        return super().clean_new_password1()


class HilaacAuthenticationForm(AuthenticationForm):
    """Strip accidental whitespace; email can be typed in the username field."""

    def clean_username(self):
        return (self.cleaned_data.get("username") or "").strip()

    def clean_password(self):
        return (self.cleaned_data.get("password") or "").strip()


class StudentRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    phone = forms.CharField(max_length=20, required=False)
    country = forms.CharField(max_length=100, required=False)

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "phone", "country", "password1", "password2")

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
        raise forms.ValidationError("Use JPG, PNG, or WebP images only.")
    if uploaded.size > PROFILE_PHOTO_MAX_BYTES:
        raise forms.ValidationError("Profile photo must be 5 MB or smaller.")
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
            "notify_course_updates": "Course updates",
            "notify_assignments": "Assignment notifications",
            "notify_certificates": "Certificate notifications",
            "notify_marketing": "Marketing emails",
            "notify_system": "System announcements",
        }
        for field in self.fields:
            self.fields[field].widget.attrs["class"] = "rounded"
            if field in labels:
                self.fields[field].label = labels[field]


# Legacy alias used by older views
ProfileForm = StudentProfileForm
