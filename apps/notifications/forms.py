from django import forms

from apps.accounts.models import User

from .models import Notification


class AdminSendNotificationForm(forms.Form):
    AUDIENCE_ALL = "all"
    AUDIENCE_STUDENTS = "students"
    AUDIENCE_INSTRUCTORS = "instructors"
    AUDIENCE_SPECIFIC = "specific"

    audience = forms.ChoiceField(
        choices=[
            (AUDIENCE_ALL, "All Users"),
            (AUDIENCE_STUDENTS, "All Students"),
            (AUDIENCE_INSTRUCTORS, "All Instructors"),
            (AUDIENCE_SPECIFIC, "Specific Users"),
        ],
        widget=forms.Select(attrs={"class": "form-input"}),
    )
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True).order_by("username"),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-input", "size": 8}),
    )
    title = forms.CharField(max_length=200, widget=forms.TextInput(attrs={"class": "form-input"}))
    message = forms.CharField(widget=forms.Textarea(attrs={"class": "form-input", "rows": 4}))
    severity = forms.ChoiceField(
        choices=Notification.Severity.choices,
        widget=forms.Select(attrs={"class": "form-input"}),
    )
    link = forms.CharField(
        required=False,
        widget=forms.URLInput(attrs={"class": "form-input", "placeholder": "https:// (optional)"}),
    )
