import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class WorkspaceJoinLink(models.Model):
    """Shareable link that grants membership directly. Only the token hash is stored."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="join_links"
    )
    token_hash = models.CharField(max_length=64, unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "workspaces_join_link"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace"],
                condition=models.Q(revoked_at__isnull=True),
                name="one_unrevoked_join_link_per_workspace",
            )
        ]

    def is_usable(self, now=None) -> bool:
        now = now or timezone.now()
        return self.revoked_at is None and self.expires_at > now
