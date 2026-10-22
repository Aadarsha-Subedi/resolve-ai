from django.apps import AppConfig


class AiConfig(AppConfig):
    name = "ai"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from ai import signals  # noqa: F401
