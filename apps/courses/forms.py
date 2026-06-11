from django import forms

from .language_defaults import active_language_queryset
from .models import Lesson, Level, Module

_INPUT = (
    "w-full px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-600 "
    "bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100"
)
_ALLOWED_IMG = (".jpg", ".jpeg", ".png", ".webp")


class CourseForm(forms.ModelForm):
    """Course (Level) create/edit form used by instructors and admins."""

    class Meta:
        model = Level
        fields = (
            "language", "name", "subtitle", "level_tag", "description",
            "learning_objectives", "skills", "target_audience", "requirements",
            "keywords", "duration_weeks", "price", "is_free", "certificate_included",
            "thumbnail", "banner",
        )
        labels = {
            "language": "Category",
            "name": "Course Title",
            "subtitle": "Subtitle",
            "level_tag": "Level",
            "learning_objectives": "Learning Objectives (one per line)",
            "skills": "Skills Acquired (one per line)",
            "target_audience": "Target Audience (one per line)",
            "requirements": "Requirements (one per line)",
            "certificate_included": "Certificate included on completion",
            "thumbnail": "Course Thumbnail",
            "banner": "Course Banner",
            "price": "Price (USD)",
            "duration_weeks": "Duration (weeks)",
        }
        widgets = {
            "language": forms.Select(attrs={"class": _INPUT}),
            "name": forms.TextInput(attrs={"class": _INPUT, "placeholder": "e.g. English Beginner"}),
            "subtitle": forms.TextInput(attrs={"class": _INPUT, "placeholder": "Short tagline"}),
            "level_tag": forms.Select(attrs={"class": _INPUT}),
            "description": forms.Textarea(attrs={"class": _INPUT, "rows": 4}),
            "learning_objectives": forms.Textarea(attrs={"class": _INPUT, "rows": 3, "placeholder": "Speak confidently in everyday situations\nWrite clear emails"}),
            "skills": forms.Textarea(attrs={"class": _INPUT, "rows": 3}),
            "target_audience": forms.Textarea(attrs={"class": _INPUT, "rows": 3}),
            "requirements": forms.Textarea(attrs={"class": _INPUT, "rows": 3}),
            "keywords": forms.TextInput(attrs={"class": _INPUT, "placeholder": "comma, separated, keywords"}),
            "duration_weeks": forms.NumberInput(attrs={"class": _INPUT}),
            "price": forms.NumberInput(attrs={"class": _INPUT}),
            "is_free": forms.CheckboxInput(attrs={"class": "rounded"}),
            "certificate_included": forms.CheckboxInput(attrs={"class": "rounded"}),
            "thumbnail": forms.FileInput(attrs={"class": "w-full text-sm", "accept": ".jpg,.jpeg,.png,.webp"}),
            "banner": forms.FileInput(attrs={"class": "w-full text-sm", "accept": ".jpg,.jpeg,.png,.webp"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["language"].queryset = active_language_queryset()
        self.fields["language"].empty_label = "Select category"
        if not (self.instance and self.instance.pk):
            self.fields["thumbnail"].required = True

    def _clean_image(self, field):
        f = self.cleaned_data.get(field)
        if f and getattr(f, "name", "") and not f.name.lower().endswith(_ALLOWED_IMG):
            raise forms.ValidationError("Use a JPG, JPEG, PNG or WEBP image.")
        return f

    def clean_thumbnail(self):
        return self._clean_image("thumbnail")

    def clean_banner(self):
        return self._clean_image("banner")


class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ("level", "title", "order", "description")
        labels = {
            "title": "Section Title",
            "description": "Section Description",
            "order": "Section Order",
        }
        widgets = {
            "level": forms.Select(attrs={"class": _INPUT}),
            "title": forms.TextInput(attrs={"class": _INPUT, "placeholder": "e.g. Introduction"}),
            "order": forms.NumberInput(attrs={"class": _INPUT}),
            "description": forms.Textarea(attrs={"class": _INPUT, "rows": 3}),
        }


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = (
            "module",
            "title",
            "description",
            "lesson_type",
            "video_file",
            "video_url",
            "thumbnail",
            "pdf_file",
            "content",
            "duration_minutes",
            "order",
            "is_published",
            "is_preview",
        )
        labels = {
            "title": "Lesson Title",
            "description": "Lesson Description",
            "content": "Lesson Notes",
            "is_preview": "Free Preview",
        }
        widgets = {
            "module": forms.HiddenInput(),
            "title": forms.TextInput(attrs={"class": _INPUT, "placeholder": "Lesson title"}),
            "description": forms.Textarea(attrs={"class": _INPUT, "rows": 2, "placeholder": "What students will learn in this lesson"}),
            "lesson_type": forms.HiddenInput(),
            "video_file": forms.FileInput(attrs={"class": "w-full text-sm", "accept": "video/mp4,video/quicktime,video/webm,.mp4,.mov,.webm", "x-ref": "videoInput", "@change": "onVideoChange"}),
            "video_url": forms.URLInput(attrs={"class": _INPUT, "placeholder": "https://..."}),
            "thumbnail": forms.FileInput(attrs={"class": "w-full text-sm", "accept": ".jpg,.jpeg,.png,.webp", "x-ref": "thumbInput", "@change": "onThumbChange"}),
            "pdf_file": forms.FileInput(attrs={"class": "w-full text-sm", "accept": ".pdf"}),
            "content": forms.Textarea(attrs={"class": _INPUT, "rows": 4, "placeholder": "Notes, instructions, or supplementary text"}),
            "duration_minutes": forms.NumberInput(attrs={"class": _INPUT}),
            "order": forms.NumberInput(attrs={"class": _INPUT}),
            "is_published": forms.CheckboxInput(attrs={"class": "rounded"}),
            "is_preview": forms.CheckboxInput(attrs={"class": "rounded"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields["lesson_type"].initial = Lesson.LessonType.VIDEO

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("is_preview"):
            lesson = self.instance
            for field in ("module", "order", "is_published"):
                if field in cleaned:
                    setattr(lesson, field, cleaned[field])
            from .preview import validate_preview_lesson

            from django.core.exceptions import ValidationError

            try:
                validate_preview_lesson(lesson, is_preview=True)
            except ValidationError as exc:
                self.add_error("is_preview", exc.messages[0])
        return cleaned
