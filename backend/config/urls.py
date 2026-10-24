"""Root URL configuration: one include per feature app under /api/."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("common.urls")),
    path("api/", include("accounts.urls")),
    path("api/", include("workspaces.urls")),
    path("api/", include("knowledge.urls")),
    path("api/", include("ai.urls")),
    path("api/", include("tickets.urls")),
    path("api/", include("email_integration.urls")),
    path("api/", include("audit.urls")),
]
