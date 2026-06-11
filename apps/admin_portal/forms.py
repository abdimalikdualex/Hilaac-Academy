from django import forms
from django.contrib.auth import get_user_model

from apps.assessments.models import Assignment
from apps.cms.models import (
    ANNOUNCEMENT_THEME_COLORS,
    ANNOUNCEMENT_THEME_LABELS,
    Announcement,
    FAQ,
    PartnerSchool,
    PlatformIntroductionVideo,
    Testimonial,
)
from apps.core.imaging import ALLOWED_IMAGE_EXTS
from apps.core.models import SiteSettings
from apps.courses.language_defaults import active_language_queryset
from apps.courses.models import Level
from apps.library.models import LibraryResource
from apps.payments.models import ExchangeRate

User = get_user_model()


def validate_image_upload(uploaded):
    """Ensure an uploaded cover/thumbnail is an allowed web image format."""
    if not uploaded or not getattr(uploaded, "name", ""):
        return uploaded
    name = uploaded.name.lower()
    if not name.endswith(ALLOWED_IMAGE_EXTS):
        raise forms.ValidationError("Use a JPG, JPEG, PNG or WEBP image.")
    return uploaded


class StudentForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "phone", "country", "date_of_birth", "is_active", "is_verified")
        widgets = {f: forms.TextInput(attrs={"class": "form-input"}) for f in ("username", "email", "first_name", "last_name", "phone", "country")}
        widgets["is_active"] = forms.CheckboxInput()
        widgets["is_verified"] = forms.CheckboxInput()
        widgets["date_of_birth"] = forms.DateInput(attrs={"class": "form-input", "type": "date"})


class InstructorForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "phone", "bio", "is_active")
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-input"}),
            "email": forms.EmailInput(attrs={"class": "form-input"}),
            "first_name": forms.TextInput(attrs={"class": "form-input"}),
            "last_name": forms.TextInput(attrs={"class": "form-input"}),
            "phone": forms.TextInput(attrs={"class": "form-input"}),
            "bio": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
            "is_active": forms.CheckboxInput(),
        }


class LevelForm(forms.ModelForm):
    class Meta:
        model = Level
        fields = (
            "language", "name", "subtitle", "level_tag", "slug", "order", "description",
            "learning_objectives", "skills", "target_audience", "requirements", "keywords",
            "thumbnail", "banner", "price", "is_free", "is_published", "is_archived",
            "certificate_included", "duration_weeks", "instructor",
        )
        labels = {
            "language": "Category",
            "name": "Course Title",
            "level_tag": "Level",
            "description": "Course Description",
            "thumbnail": "Course Thumbnail",
            "banner": "Course Banner",
            "duration_weeks": "Duration (weeks)",
            "price": "Price (USD)",
        }
        widgets = {
            "language": forms.Select(attrs={"class": "form-input"}),
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "level_tag": forms.Select(attrs={"class": "form-input"}),
            "slug": forms.TextInput(attrs={"class": "form-input"}),
            "order": forms.NumberInput(attrs={"class": "form-input"}),
            "duration_weeks": forms.NumberInput(attrs={"class": "form-input"}),
            "price": forms.NumberInput(attrs={"class": "form-input"}),
            "description": forms.Textarea(attrs={"rows": 3, "class": "form-input"}),
            "learning_objectives": forms.Textarea(attrs={"rows": 3, "class": "form-input"}),
            "skills": forms.Textarea(attrs={"rows": 3, "class": "form-input"}),
            "target_audience": forms.Textarea(attrs={"rows": 3, "class": "form-input"}),
            "requirements": forms.Textarea(attrs={"rows": 3, "class": "form-input"}),
            "subtitle": forms.TextInput(attrs={"class": "form-input"}),
            "keywords": forms.TextInput(attrs={"class": "form-input"}),
            "thumbnail": forms.FileInput(attrs={"class": "form-input", "accept": ".jpg,.jpeg,.png,.webp"}),
            "banner": forms.FileInput(attrs={"class": "form-input", "accept": ".jpg,.jpeg,.png,.webp"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["language"].queryset = active_language_queryset()
        self.fields["language"].empty_label = "Select category"
        # Cover image is required when creating a new course.
        if not (self.instance and self.instance.pk):
            self.fields["thumbnail"].required = True

    def clean_thumbnail(self):
        return validate_image_upload(self.cleaned_data.get("thumbnail"))

    def clean_banner(self):
        return validate_image_upload(self.cleaned_data.get("banner"))


class SiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = "__all__"
        widgets = {"footer_text": forms.Textarea(attrs={"rows": 3, "class": "form-input"}), "tagline": forms.TextInput(attrs={"class": "form-input"})}


class LibraryResourceForm(forms.ModelForm):
    class Meta:
        model = LibraryResource
        fields = ("title", "category", "language", "description", "file", "is_published")


class FAQForm(forms.ModelForm):
    class Meta:
        model = FAQ
        fields = ("question", "answer", "order", "is_active")
        widgets = {"answer": forms.Textarea(attrs={"rows": 4, "class": "form-input"})}


class TestimonialForm(forms.ModelForm):
    class Meta:
        model = Testimonial
        fields = ("student_name", "course_name", "quote", "rating", "is_featured", "order")


class PartnerSchoolForm(forms.ModelForm):
    class Meta:
        model = PartnerSchool
        fields = ("name", "logo", "website_url", "country", "display_order", "is_active")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "website_url": forms.URLInput(attrs={"class": "form-input", "placeholder": "https://"}),
            "country": forms.TextInput(attrs={"class": "form-input"}),
            "display_order": forms.NumberInput(attrs={"class": "form-input", "min": 0}),
        }
        help_texts = {
            "logo": "PNG or SVG with transparent background recommended (min 500×500).",
        }


class AnnouncementForm(forms.ModelForm):
    color_theme = forms.ChoiceField(
        choices=[(key, ANNOUNCEMENT_THEME_LABELS[key]) for key in ANNOUNCEMENT_THEME_COLORS],
        label="Color theme",
        widget=forms.RadioSelect,
    )

    class Meta:
        model = Announcement
        fields = (
            "title",
            "message",
            "announcement_type",
            "link_url",
            "start_date",
            "end_date",
            "display_order",
            "is_active",
        )
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-input"}),
            "message": forms.TextInput(attrs={"class": "form-input"}),
            "announcement_type": forms.Select(attrs={"class": "form-input"}),
            "link_url": forms.URLInput(attrs={"class": "form-input", "placeholder": "https:// (optional)"}),
            "start_date": forms.DateTimeInput(
                attrs={"class": "form-input", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "end_date": forms.DateTimeInput(
                attrs={"class": "form-input", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "display_order": forms.NumberInput(attrs={"class": "form-input", "min": 0}),
        }
        help_texts = {
            "message": "Shown in the scrolling ticker. English and Somali supported.",
            "end_date": "Leave blank for no expiry.",
            "link_url": "Optional — makes the ticker item clickable.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["start_date"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["end_date"].input_formats = ["%Y-%m-%dT%H:%M"]
        if self.instance and self.instance.pk:
            self.initial["color_theme"] = self.instance.get_theme_key()
        self.order_fields(
            [
                "title",
                "message",
                "announcement_type",
                "color_theme",
                "link_url",
                "start_date",
                "end_date",
                "display_order",
                "is_active",
            ]
        )

    def save(self, commit=True):
        announcement = super().save(commit=False)
        theme = self.cleaned_data.get("color_theme")
        if theme in ANNOUNCEMENT_THEME_COLORS:
            bg, txt = ANNOUNCEMENT_THEME_COLORS[theme]
            announcement.background_color = bg
            announcement.text_color = txt
        if commit:
            announcement.save()
        return announcement


class PlatformIntroductionVideoForm(forms.ModelForm):
    class Meta:
        model = PlatformIntroductionVideo
        fields = (
            "title",
            "title_somali",
            "description",
            "video_file",
            "thumbnail",
            "is_active",
        )
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-input"}),
            "title_somali": forms.TextInput(attrs={"class": "form-input"}),
            "description": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
            "video_file": forms.FileInput(
                attrs={"class": "w-full text-sm", "accept": "video/mp4,video/webm,.mp4,.webm"}
            ),
            "thumbnail": forms.FileInput(
                attrs={"class": "w-full text-sm", "accept": ".jpg,.jpeg,.png,.webp"}
            ),
        }
        help_texts = {
            "video_file": "MP4 or WebM. Only one video can be active on the landing page.",
            "thumbnail": "Cover image with play overlay before the video starts.",
            "is_active": "Activating this video deactivates any other active intro video.",
        }

    def clean_thumbnail(self):
        return validate_image_upload(self.cleaned_data.get("thumbnail"))


class ExchangeRateForm(forms.ModelForm):
    class Meta:
        model = ExchangeRate
        fields = ("to_currency", "rate", "is_active")
        labels = {
            "to_currency": "Currency Code",
            "rate": "1 USD equals",
            "is_active": "Active",
        }
        widgets = {
            "to_currency": forms.TextInput(attrs={"class": "form-input", "placeholder": "KES"}),
            "rate": forms.NumberInput(attrs={"class": "form-input", "step": "0.0001"}),
        }
