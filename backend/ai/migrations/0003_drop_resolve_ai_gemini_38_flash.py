from django.db import migrations

REMOVED = "gemini-3.8-flash"
DEFAULT = "gemini-3.5-flash-lite"


def reset_removed_model(apps, schema_editor):
    """Resolve AI mode no longer offers the removed model: settings that picked it get the default."""
    apps.get_model("ai", "UserWorkspaceLLMSettings").objects.filter(
        resolve_ai_model=REMOVED
    ).update(resolve_ai_model=DEFAULT)


class Migration(migrations.Migration):
    dependencies = [("ai", "0002_llm_keys_per_provider")]

    operations = [migrations.RunPython(reset_removed_model, migrations.RunPython.noop)]
