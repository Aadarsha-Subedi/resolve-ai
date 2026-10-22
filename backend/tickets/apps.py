from django.apps import AppConfig


class TicketsConfig(AppConfig):
    name = "tickets"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from tickets import signals  # noqa: F401
