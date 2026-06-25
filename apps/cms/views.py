import logging

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Count, Q
from django.db.utils import OperationalError, ProgrammingError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

from apps.core.cache_sync import home_cache_key
from apps.courses.models import Level

from .models import FAQ, LegalPage, PlatformIntroductionVideo, SiteStatistic, Testimonial

User = get_user_model()
HOME_CACHE_TTL = 300


def _get_platform_video():
    try:
        return PlatformIntroductionVideo.get_active()
    except (OperationalError, ProgrammingError):
        logger.warning("PlatformIntroductionVideo table missing — run python manage.py migrate cms")
        return None


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

    platform_video = _get_platform_video()

    return {
        "featured_courses": list(featured_courses),
        "statistics": list(SiteStatistic.objects.filter(is_active=True)),
        "testimonials": list(Testimonial.objects.filter(is_featured=True)),
        "faqs": list(FAQ.objects.filter(is_active=True)),
        "instructors": list(instructors),
        "platform_video": platform_video,
        "query": query,
    }


@require_POST
def platform_video_track(request):
    video = get_object_or_404(PlatformIntroductionVideo, pk=request.POST.get("video_id"), is_active=True)
    event = request.POST.get("event", "").strip()

    if event == "impression":
        video.record_impression()
    elif event == "play":
        video.record_play()
    elif event == "progress":
        try:
            seconds = max(0, int(request.POST.get("seconds", 0)))
        except (TypeError, ValueError):
            seconds = 0
        if seconds:
            video.record_watch_seconds(seconds)
    elif event == "complete":
        video.record_completion()
    else:
        return JsonResponse({"ok": False, "error": "invalid_event"}, status=400)

    return JsonResponse({"ok": True})


def home(request):
    query = request.GET.get("q", "").strip()
    cache_key = home_cache_key()

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


def legal_page(request, page_type):
    page = LegalPage.get_page(page_type)
    template_map = {
        LegalPage.PageType.PRIVACY: "cms/privacy_policy.html",
        LegalPage.PageType.TERMS: "cms/terms_conditions.html",
    }
    template_name = template_map.get(page_type, "cms/privacy_policy.html")
    return render(
        request,
        template_name,
        {
            "legal_page": page,
            "page_title": page.title,
            "last_updated": page.last_updated,
        },
    )
