from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from accounts.models import User
from accounts.services import deletion_service, hooks


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user: User, **kwargs) -> None:
    deletion_service.cancel_deletion(user)
    hooks.emit(user, hooks.ACTION_LOGIN)
