from allauth.account.signals import user_logged_in
from django.dispatch import receiver

from accounts.services import hooks as account_hooks
from workspaces.services import demo_service


@receiver(user_logged_in)
def provision_demo(sender, request, user, **kwargs) -> None:
    # allauth's signal, not Django's: only a real Google sign-in creates the demo, never
    # `force_login` in tests or the admin.
    demo_service.provision_on_sign_in(user)


@receiver(account_hooks.account_event)
def remove_demo_with_account(sender, user, action, **kwargs) -> None:
    if action == account_hooks.ACTION_DELETED:
        demo_service.delete_demos_of(user)
