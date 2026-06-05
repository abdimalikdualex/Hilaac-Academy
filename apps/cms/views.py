from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.shortcuts import render

from apps.courses.models import Level

from .models import FAQ, SiteStatistic, Testimonial

User = get_user_model()


def home(request):
    query = request.GET.get("q", "").strip()
    published = Level.objects.filter(is_published=True, is_archived=False).select_related("language")

    featured_courses = published
    if query:
        featured_courses = published.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(keywords__icontains=query)
            | Q(language__name__icontains=query)
        )
    featured_courses = featured_courses[:6]

    instructors = (
        User.objects.filter(role=User.Role.INSTRUCTOR, is_active=True)
        .annotate(student_count=Count("assigned_levels__enrollments"))[:4]
    )

    context = {
        "featured_courses": featured_courses,
        "statistics": SiteStatistic.objects.filter(is_active=True),
        "testimonials": Testimonial.objects.filter(is_featured=True),
        "faqs": FAQ.objects.filter(is_active=True),
        "instructors": instructors,
        "query": query,
    }
    return render(request, "cms/home.html", context)
