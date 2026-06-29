from django import forms

from .models import Assignment, AssignmentSubmission, Quiz

_INPUT = "w-full px-4 py-2 rounded-lg border border-slate-300 bg-white text-slate-900"
_SUBMISSION_EXTS = (
    ".pdf", ".doc", ".docx", ".ppt", ".pptx", ".zip",
    ".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm",
)
_ATTACHMENT_EXTS = (".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png", ".webp")


def _ext_ok(name, allowed):
    if not name or "." not in name:
        return False
    return name.rsplit(".", 1)[-1].lower() in {e.lstrip(".") for e in allowed}


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = (
            "title",
            "description",
            "instructions",
            "due_date",
            "max_score",
            "attachment",
            "allow_resubmit",
            "is_published",
        )
        widgets = {
            "title": forms.TextInput(attrs={"class": _INPUT}),
            "description": forms.Textarea(attrs={"class": _INPUT, "rows": 3}),
            "instructions": forms.Textarea(attrs={"class": _INPUT, "rows": 4}),
            "due_date": forms.DateTimeInput(attrs={"class": _INPUT, "type": "datetime-local"}),
            "max_score": forms.NumberInput(attrs={"class": _INPUT, "min": 1}),
            "attachment": forms.FileInput(attrs={"class": "w-full text-sm", "accept": ".pdf,.doc,.docx,.jpg,.jpeg,.png,.webp"}),
            "allow_resubmit": forms.CheckboxInput(attrs={"class": "rounded"}),
            "is_published": forms.CheckboxInput(attrs={"class": "rounded"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["due_date"].input_formats = ["%Y-%m-%dT%H:%M"]

    def clean_attachment(self):
        uploaded = self.cleaned_data.get("attachment")
        if uploaded and not _ext_ok(uploaded.name, _ATTACHMENT_EXTS):
            raise forms.ValidationError("Use PDF, DOCX, or image files for attachments.")
        return uploaded


class AssignmentSubmissionForm(forms.ModelForm):
    class Meta:
        model = AssignmentSubmission
        fields = ("file", "notes")
        widgets = {
            "file": forms.FileInput(
                attrs={
                    "class": "w-full text-sm",
                    "accept": ".pdf,.doc,.docx,.ppt,.pptx,.zip,.jpg,.jpeg,.png,.webp,.mp4,.mov,.webm",
                }
            ),
            "notes": forms.Textarea(attrs={"class": _INPUT, "rows": 3, "placeholder": "Optional notes for your instructor"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.file:
            self.fields["file"].required = False

    def clean_file(self):
        uploaded = self.cleaned_data.get("file")
        if not uploaded and not (self.instance and self.instance.file):
            raise forms.ValidationError("Please upload your assignment file.")
        if uploaded and not _ext_ok(uploaded.name, _SUBMISSION_EXTS):
            raise forms.ValidationError("Allowed: PDF, Word, PowerPoint, ZIP, images, or video (MP4/MOV/WebM).")
        if uploaded and uploaded.size > 25 * 1024 * 1024:
            raise forms.ValidationError("File must be 25 MB or smaller.")
        return uploaded


class AssignmentGradeForm(forms.Form):
    grade = forms.DecimalField(min_value=0, widget=forms.NumberInput(attrs={"class": _INPUT, "step": "0.01"}))
    feedback = forms.CharField(required=False, widget=forms.Textarea(attrs={"class": _INPUT, "rows": 4}))
    status = forms.ChoiceField(
        choices=[
            (AssignmentSubmission.Status.GRADED, "Graded"),
            (AssignmentSubmission.Status.RESUBMIT, "Return for Correction"),
            (AssignmentSubmission.Status.APPROVED, "Approved"),
        ],
        widget=forms.Select(attrs={"class": _INPUT}),
    )

    def __init__(self, *args, max_score=100, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_score = max_score
        self.fields["grade"].widget.attrs["max"] = max_score

    def clean_grade(self):
        grade = self.cleaned_data["grade"]
        if grade > self.max_score:
            raise forms.ValidationError(f"Score cannot exceed {self.max_score} marks.")
        return grade


class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = (
            "title",
            "description",
            "pass_mark",
            "time_limit_minutes",
            "max_attempts",
            "randomize_questions",
            "questions_per_attempt",
            "is_published",
            "show_correct_answers",
            "is_final",
        )
        widgets = {
            "title": forms.TextInput(attrs={"class": _INPUT}),
            "description": forms.Textarea(attrs={"class": _INPUT, "rows": 3}),
            "pass_mark": forms.NumberInput(attrs={"class": _INPUT, "min": 0, "max": 100}),
            "time_limit_minutes": forms.NumberInput(attrs={"class": _INPUT, "min": 1}),
            "max_attempts": forms.NumberInput(attrs={"class": _INPUT, "min": 1}),
            "is_published": forms.CheckboxInput(attrs={"class": "rounded"}),
            "show_correct_answers": forms.CheckboxInput(attrs={"class": "rounded"}),
            "is_final": forms.CheckboxInput(attrs={"class": "rounded"}),
            "randomize_questions": forms.CheckboxInput(attrs={"class": "rounded"}),
            "questions_per_attempt": forms.NumberInput(attrs={"class": _INPUT, "min": 1}),
        }
