import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models

from accounts.constants.settings import DISPLAY_NAME_MAX_LENGTH
from common.email.utils import normalize_email
from common.models import TimeStampModel


class UserManager(BaseUserManager):
    """Every row, including accounts pending deletion (needed to cancel a deletion)."""

    use_in_migrations = True

    def create_user(self, email: str, **extra_fields) -> User:
        if not email:
            raise ValueError("An email address is required.")
        user = self.model(email=normalize_email(email), **extra_fields)
        user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, **extra_fields) -> User:
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, **extra_fields)


class VisibleUserManager(UserManager):
    """Hides accounts that are waiting to be deleted."""

    def get_queryset(self) -> models.QuerySet:
        return super().get_queryset().filter(deletion_requested_at__isnull=True)


class User(AbstractBaseUser, PermissionsMixin, TimeStampModel):
    """A person who signs in with Google. No password and no username."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=DISPLAY_NAME_MAX_LENGTH, blank=True)
    avatar_url = models.URLField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    deletion_requested_at = models.DateTimeField(null=True, blank=True)
    # Set once the first-sign-in demo workspace exists, so deleting it is never undone
    # by the next sign-in.
    demo_provisioned_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()
    visible = VisibleUserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        db_table = "accounts_user"

    def __str__(self) -> str:
        return self.email

    @property
    def is_pending_deletion(self) -> bool:
        return self.deletion_requested_at is not None
