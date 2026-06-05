from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render

from .models import LibraryResource


@login_required
def library_home(request):
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")

    resources = LibraryResource.objects.filter(is_published=True).select_related("language")
    if query:
        resources = resources.filter(Q(title__icontains=query) | Q(description__icontains=query))
    if category:
        resources = resources.filter(category=category)

    return render(
        request,
        "library/home.html",
        {
            "resources": resources,
            "query": query,
            "category": category,
            "categories": LibraryResource.Category.choices,
        },
    )
