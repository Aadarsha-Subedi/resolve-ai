"""Root URL configuration: one include per feature app under /api/."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("common.urls")),
    path("api/", include("accounts.urls")),
]
