from django.urls import path

from email_integration.views import gmail

urlpatterns = [
    path("email/gmail/", gmail.GmailStatusView.as_view(), name="gmail_status"),
    path("email/gmail/sync/", gmail.GmailSyncView.as_view(), name="gmail_sync"),
    path("email/gmail/push/", gmail.GmailPushView.as_view(), name="gmail_push"),
    path("email/review/", gmail.ReviewListView.as_view(), name="email_review_list"),
    path(
        "email/review/<uuid:review_id>/attach/",
        gmail.ReviewAttachView.as_view(),
        name="email_review_attach",
    ),
    path(
        "email/review/<uuid:review_id>/dismiss/",
        gmail.ReviewDismissView.as_view(),
        name="email_review_dismiss",
    ),
    path(
        "workspaces/<uuid:workspace_id>/tickets/<uuid:ticket_id>/messages/<uuid:message_id>/resend/",
        gmail.ResendMessageView.as_view(),
        name="ticket_message_resend",
    ),
]
