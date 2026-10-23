from django.apps import AppConfig


class TicketsConfig(AppConfig):
    name = "tickets"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from tickets import signals  # noqa: F401
        from tickets.services import demo_seed
        from workspaces.services.demo_service import DemoContent, register_demo_content

        register_demo_content(
            DemoContent(name="tickets", seed=demo_seed.seed, clear=demo_seed.clear)
        )
