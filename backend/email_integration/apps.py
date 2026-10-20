from django.apps import AppConfig


class EmailIntegrationConfig(AppConfig):
    name = "email_integration"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from email_integration import signals  # noqa: F401
