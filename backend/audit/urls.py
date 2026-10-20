from django.urls import path

from audit.views.dashboard import DashboardView
from audit.views.events import AuditEventListView

urlpatterns = [
    path(
        "workspaces/<uuid:workspace_id>/audit/",
        AuditEventListView.as_view(),
        name="audit_list",
    ),
    path(
        "workspaces/<uuid:workspace_id>/dashboard/",
        DashboardView.as_view(),
        name="dashboard",
    ),
]
