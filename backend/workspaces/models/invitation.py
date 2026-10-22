import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class WorkspaceInvitation(models.Model):
    """Invitation for one Google account. `email` is as typed (lower-cased);
    `email_key` is the canonical mailbox key used to match the signed-in user."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="invitations"
    )
    email = models.EmailField()
    email_key = models.EmailField()
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    # Set when the owner revokes the invitation or the invitee declines it.
    closed_at = models.DateTimeField(null=True, blank=True)
    # Set when the invitation email left the inviter's Gmail; null means it was not
    # sent (no connected Gmail, delivery failed) and the invitee finds it in the app.
    notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "workspaces_invitation"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "email_key"],
                condition=models.Q(accepted_at__isnull=True, closed_at__isnull=True),
                name="one_open_invitation_per_mailbox",
            )
        ]
        indexes = [models.Index(fields=["email_key"])]

    def is_usable(self, now=None) -> bool:
        now = now or timezone.now()
        return (
            self.accepted_at is None
            and self.closed_at is None
            and self.expires_at > now
        )
