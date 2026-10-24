from django.apps import AppConfig


class EmailIntegrationConfig(AppConfig):
    name = "email_integration"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from email_integration import signals  # noqa: F401
        from email_integration.services.overview import gmail_status_block
        from tickets.services import overview_service

        overview_service.register_extra("email", gmail_status_block)
