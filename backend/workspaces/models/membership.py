import uuid

from django.conf import settings
from django.db import models

from common.models import TimeStampModel
from workspaces.constants.roles import MembershipStatus, Role


class WorkspaceMembership(TimeStampModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    status = models.CharField(
        max_length=10, choices=MembershipStatus.choices, default=MembershipStatus.ACTIVE
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workspaces_membership"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "user"], name="unique_workspace_user"
            ),
            models.UniqueConstraint(
                fields=["workspace"],
                condition=models.Q(role=Role.OWNER, status=MembershipStatus.ACTIVE),
                name="one_active_owner_per_workspace",
            ),
        ]
        indexes = [models.Index(fields=["user", "status"])]

    @property
    def is_active(self) -> bool:
        return self.status == MembershipStatus.ACTIVE

    @property
    def is_owner(self) -> bool:
        return self.role == Role.OWNER and self.is_active
