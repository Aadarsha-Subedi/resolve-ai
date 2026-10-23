from django.apps import AppConfig


class WorkspacesConfig(AppConfig):
    name = "workspaces"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from accounts.services.hooks import register_ownership_check
        from workspaces.services.ownership import account_ownership_blocker

        register_ownership_check(account_ownership_blocker)

        from workspaces import signals  # noqa: F401
