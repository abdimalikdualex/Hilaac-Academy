from django import forms

from .models import DiscussionReply, DiscussionThread, LiveClassSession

_INPUT = "w-full px-4 py-2 rounded-lg border border-slate-300 bg-white text-slate-900"


class DiscussionThreadForm(forms.ModelForm):
    class Meta:
        model = DiscussionThread
        fields = ("title", "body")
        widgets = {
            "title": forms.TextInput(attrs={"class": _INPUT, "placeholder": "Question title"}),
            "body": forms.Textarea(attrs={"class": _INPUT, "rows": 4, "placeholder": "Describe your question..."}),
        }


class DiscussionReplyForm(forms.ModelForm):
    class Meta:
        model = DiscussionReply
        fields = ("body",)
        widgets = {
            "body": forms.Textarea(attrs={"class": _INPUT, "rows": 3, "placeholder": "Write your reply..."}),
        }


class LiveClassSessionForm(forms.ModelForm):
    class Meta:
        model = LiveClassSession
        fields = ("title", "description", "starts_at", "duration_minutes", "meeting_url", "platform", "is_published")
        widgets = {
            "title": forms.TextInput(attrs={"class": _INPUT}),
            "description": forms.Textarea(attrs={"class": _INPUT, "rows": 3}),
            "starts_at": forms.DateTimeInput(attrs={"class": _INPUT, "type": "datetime-local"}),
            "duration_minutes": forms.NumberInput(attrs={"class": _INPUT, "min": 15}),
            "meeting_url": forms.URLInput(attrs={"class": _INPUT, "placeholder": "https://zoom.us/j/..."}),
            "platform": forms.Select(attrs={"class": _INPUT}),
            "is_published": forms.CheckboxInput(attrs={"class": "rounded"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["starts_at"].input_formats = ["%Y-%m-%dT%H:%M"]
