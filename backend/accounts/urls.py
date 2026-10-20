from django.urls import path

from accounts.views.google import GoogleCallbackView, GoogleStartView
from accounts.views.profile import MeView
from accounts.views.session import (
    CsrfView,
    LogoutAllView,
    LogoutView,
    SessionDetailView,
    SessionListView,
)

urlpatterns = [
    path("csrf/", CsrfView.as_view(), name="csrf"),
    path("auth/google/start/", GoogleStartView.as_view(), name="google_start"),
    # allauth builds the OAuth redirect URI from the URL named "google_callback".
    path(
        "auth/google/login/callback/",
        GoogleCallbackView.as_view(),
        name="google_callback",
    ),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/logout-all/", LogoutAllView.as_view(), name="logout_all"),
    path("auth/sessions/", SessionListView.as_view(), name="session_list"),
    path(
        "auth/sessions/<int:session_id>/",
        SessionDetailView.as_view(),
        name="session_detail",
    ),
    path("me/", MeView.as_view(), name="me"),
]
