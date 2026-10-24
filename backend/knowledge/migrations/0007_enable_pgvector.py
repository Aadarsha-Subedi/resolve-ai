from django.db import migrations


def enable_pgvector(apps, schema_editor):
    # Postgres only; the SQLite test escape hatch has no vector type.
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("CREATE EXTENSION IF NOT EXISTS vector")


class Migration(migrations.Migration):
    dependencies = [("knowledge", "0006_ask_history")]

    operations = [migrations.RunPython(enable_pgvector, migrations.RunPython.noop)]
