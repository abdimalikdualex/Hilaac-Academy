from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Count, Q
from django.shortcuts import render

from apps.courses.models import Level

from .models import FAQ, SiteStatistic, Testimonial

User = get_user_model()
HOME_CACHE_TTL = 300


def _home_context(query=""):
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

    return {
        "featured_courses": list(featured_courses),
        "statistics": list(SiteStatistic.objects.filter(is_active=True)),
        "testimonials": list(Testimonial.objects.filter(is_featured=True)),
        "faqs": list(FAQ.objects.filter(is_active=True)),
        "instructors": list(instructors),
        "query": query,
    }


def home(request):
    query = request.GET.get("q", "").strip()
    cache_key = "cms:home:context"

    if not query:
        cached = cache.get(cache_key)
        if cached:
            ctx = cached.copy()
            ctx["query"] = query
            return render(request, "cms/home.html", ctx)

    context = _home_context(query)
    if not query:
        cache.set(cache_key, context, HOME_CACHE_TTL)

    return render(request, "cms/home.html", context)
