from django.urls import path

from ai.views import settings

_W = "workspaces/<uuid:workspace_id>/llm/"

urlpatterns = [
    path(_W, settings.LLMSettingsView.as_view(), name="llm_settings"),
    path(_W + "key/", settings.LLMKeyView.as_view(), name="llm_key"),
]
