"""Root URL configuration. Each app's routes are included under /api/v1/."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("_allauth/", include("allauth.headless.urls")),
    path("api/v1/", include("core.urls")),
    path("api/v1/", include("accounts.urls")),
]
