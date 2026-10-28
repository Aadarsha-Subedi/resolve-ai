from django.urls import path

from ai.views import settings, usage

_W = "workspaces/<uuid:workspace_id>/llm/"

urlpatterns = [
    path(_W, settings.LLMSettingsView.as_view(), name="llm_settings"),
    path(_W + "keys/<str:provider>/", settings.LLMKeyView.as_view(), name="llm_key"),
    path(
        "workspaces/<uuid:workspace_id>/ai/usage/",
        usage.UsageLogListView.as_view(),
        name="ai_usage",
    ),
]
