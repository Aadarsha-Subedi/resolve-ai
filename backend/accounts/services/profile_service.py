from accounts.models import User
from accounts.services import hooks


def update_display_name(user: User, display_name: str) -> User:
    user.display_name = display_name
    user.save(update_fields=["display_name", "updated_at"])
    hooks.emit(user, hooks.ACTION_PROFILE_UPDATED)
    return user
