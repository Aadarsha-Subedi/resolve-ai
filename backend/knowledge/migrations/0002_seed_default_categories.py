from django.db import migrations
from django.template.defaultfilters import slugify

# Frozen copy: migrations must not import app code that can change later.
DEFAULT_CATEGORIES = ["General", "Getting started", "Billing", "Troubleshooting", "FAQ"]


def seed(apps, schema_editor):
    Workspace = apps.get_model("workspaces", "Workspace")
    Category = apps.get_model("knowledge", "KnowledgeCategory")
    for workspace_id in Workspace.objects.values_list("pk", flat=True):
        for name in DEFAULT_CATEGORIES:
            Category.objects.get_or_create(
                workspace_id=workspace_id, slug=slugify(name), defaults={"name": name}
            )


class Migration(migrations.Migration):
    dependencies = [("knowledge", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
