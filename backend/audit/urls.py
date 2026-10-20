from django.urls import path

from audit.views.events import AuditEventListView

urlpatterns = [
    path(
        "workspaces/<uuid:workspace_id>/audit/",
        AuditEventListView.as_view(),
        name="audit_list",
    ),
]
