from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="dataset-list", permanent=False)),
    path("admin/", admin.site.urls),

    # Auth: login/logout using the templates in templates/registration/
    path("accounts/", include("django.contrib.auth.urls")),

    # HTML pages
    path("datasets/", include("datasets.page_urls")),
    path("review/", include("workflow.page_urls")),
    path("artifacts/", include("artifacts.page_urls")),
    path("analysis/", include("analysis.page_urls")),

    # REST API (for future use: analysis pages, external clients)
    path("api/", include("datasets.urls")),
    path("api/", include("workflow.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
