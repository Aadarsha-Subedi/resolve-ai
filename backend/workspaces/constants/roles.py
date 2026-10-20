from django.db import models


class Role(models.TextChoices):
    OWNER = "owner", "Owner"
    MEMBER = "member", "Member"


class MembershipStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    REMOVED = "removed", "Removed"
