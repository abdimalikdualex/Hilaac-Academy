from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.cms.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("student/", include("apps.accounts.student_urls")),
    path("courses/", include("apps.courses.urls")),
    path("dashboard/", include("apps.learning.urls")),
    path("quizzes/", include("apps.assessments.urls")),
    path("payments/", include("apps.payments.urls")),
    path("certificates/", include("apps.certificates.urls")),
    path("library/", include("apps.library.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("admin-portal/", include("apps.admin_portal.urls")),
    path("admin-dashboard/", RedirectView.as_view(url="/admin-portal/", permanent=False)),
    path("admin-dashboard/courses/", RedirectView.as_view(url="/admin-portal/courses/", permanent=False)),
    path("admin-portal/courses/", include("apps.courses.manage_urls")),
    path("instructor/", include("apps.admin_portal.instructor_urls")),
    path("api/", include("apps.core.api_urls")),
    path("secure-media/", include("apps.core.media_urls")),
]

if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "Hilaac Academy Admin"
admin.site.site_title = "Hilaac Academy"
admin.site.index_title = "Platform Management"

handler404 = "apps.core.views.page_not_found"
handler500 = "apps.core.views.server_error"
