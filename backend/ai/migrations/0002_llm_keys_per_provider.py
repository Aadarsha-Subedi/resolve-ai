import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


def move_keys(apps, schema_editor):
    """Each stored own key becomes a row of the new table; its provider becomes the active one."""
    Settings = apps.get_model("ai", "UserWorkspaceLLMSettings")
    Key = apps.get_model("ai", "UserWorkspaceLLMKey")
    for row in Settings.objects.exclude(own_key_encrypted=""):
        Key.objects.create(
            workspace_id=row.workspace_id,
            user_id=row.user_id,
            provider=row.own_provider,
            model=row.own_model,
            key_encrypted=row.own_key_encrypted,
            key_last4=row.own_key_last4,
            checked_at=row.own_key_checked_at or timezone.now(),
        )


class Migration(migrations.Migration):
    dependencies = [
        ("ai", "0001_initial"),
        ("workspaces", "0005_workspace_search_language"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserWorkspaceLLMKey",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid7,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("provider", models.CharField(max_length=20)),
                ("model", models.CharField(max_length=60)),
                ("key_encrypted", models.TextField()),
                ("key_last4", models.CharField(max_length=4)),
                ("checked_at", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="workspaces.workspace",
                    ),
                ),
            ],
            options={"ordering": ["created_at", "id"]},
        ),
        migrations.AddConstraint(
            model_name="userworkspacellmkey",
            constraint=models.UniqueConstraint(
                fields=("workspace", "user", "provider"),
                name="ai_llm_key_ws_user_provider_uniq",
            ),
        ),
        migrations.RunPython(move_keys, migrations.RunPython.noop),
        migrations.RenameField(
            model_name="userworkspacellmsettings",
            old_name="own_provider",
            new_name="active_provider",
        ),
        migrations.RemoveField(model_name="userworkspacellmsettings", name="own_model"),
        migrations.RemoveField(
            model_name="userworkspacellmsettings", name="own_key_encrypted"
        ),
        migrations.RemoveField(
            model_name="userworkspacellmsettings", name="own_key_last4"
        ),
        migrations.RemoveField(
            model_name="userworkspacellmsettings", name="own_key_checked_at"
        ),
    ]
