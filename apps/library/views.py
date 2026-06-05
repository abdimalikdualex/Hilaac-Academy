from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render

from apps.core.pagination import DEFAULT_PAGE_SIZE, paginate_queryset

from .models import LibraryResource


@login_required
def library_home(request):
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")

    resources = LibraryResource.objects.filter(is_published=True).select_related("language").order_by("-created_at")
    if query:
        resources = resources.filter(Q(title__icontains=query) | Q(description__icontains=query))
    if category:
        resources = resources.filter(category=category)

    page = paginate_queryset(request, resources, per_page=DEFAULT_PAGE_SIZE)

    return render(
        request,
        "library/home.html",
        {
            "resources": page,
            "page": page,
            "query": query,
            "category": category,
            "categories": LibraryResource.Category.choices,
        },
    )
