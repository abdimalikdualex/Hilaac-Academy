"""Shared pagination helpers."""
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

DEFAULT_PAGE_SIZE = 12
ADMIN_PAGE_SIZE = 20
AUDIT_PAGE_SIZE = 25
NOTIFICATION_PAGE_SIZE = 15


def paginate_queryset(request, queryset, per_page=DEFAULT_PAGE_SIZE, page_param="page"):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get(page_param, 1)
    try:
        return paginator.page(page_number)
    except PageNotAnInteger:
        return paginator.page(1)
    except EmptyPage:
        return paginator.page(paginator.num_pages)
