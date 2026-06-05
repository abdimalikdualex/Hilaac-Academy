import django, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hilaac_academy.settings")
django.setup()

from apps.courses.models import Level, Lesson, CourseReview
from apps.accounts.models import User

level = Level.objects.filter(slug="a1", language__slug="english").first() or Level.objects.first()
print("Level:", level)

lessons = Lesson.objects.filter(module__level=level, is_published=True).order_by("module__order", "order")
flagged = 0
for ls in lessons[:2]:
    ls.is_preview = True
    ls.save(update_fields=["is_preview"])
    flagged += 1
    print("  preview:", ls.title)
print("Flagged", flagged, "preview lessons")

# Add a sample review from the student
student = User.objects.filter(username="student").first()
if student:
    CourseReview.objects.update_or_create(
        student=student, level=level,
        defaults={"rating": 5, "comment": "Excellent course, very clear lessons!"},
    )
    print("Review added by", student)
print("DONE")
