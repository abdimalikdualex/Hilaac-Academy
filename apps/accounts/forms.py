from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


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


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone", "country", "date_of_birth", "profile_photo")
