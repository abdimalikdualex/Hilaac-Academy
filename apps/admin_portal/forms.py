from django import forms
from django.contrib.auth import get_user_model

from apps.assessments.models import Assignment
from apps.cms.models import FAQ, Testimonial
from apps.core.imaging import ALLOWED_IMAGE_EXTS
from apps.core.models import SiteSettings
from apps.courses.models import Language, Level
from apps.library.models import LibraryResource

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
            "price": "Price (KES)",
        }
        widgets = {
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
