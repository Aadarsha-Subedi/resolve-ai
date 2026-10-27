import logging

from django.db import migrations, models

from knowledge.services.chunk_service import BM25_TERMS_SQL

logger = logging.getLogger(__name__)

BM25_INDEX = "knowledge_chunk_bm25_idx"


def enable_bm25(apps, schema_editor):
    """Backfill `bm25_terms` and build the ParadeDB BM25 index.

    Postgres only. When the `pg_search` extension is not installed (a plain Postgres or
    pgvector image) the index is skipped and the word search keeps using the tsvector."""
    connection = schema_editor.connection
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_available_extensions WHERE name = 'pg_search'")
        if cursor.fetchone() is None:
            logger.warning("pg_search is not installed: BM25 index not created")
            return
        cursor.execute("SELECT id FROM knowledge_chunk WHERE search_vector IS NOT NULL")
        ids = [row[0] for row in cursor.fetchall()]
        if ids:
            from knowledge.constants.settings import BM25_HEADING_BOOST

            cursor.execute(BM25_TERMS_SQL, [BM25_HEADING_BOOST, ids])
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_search")
        cursor.execute(
            f"CREATE INDEX IF NOT EXISTS {BM25_INDEX} ON knowledge_chunk "
            "USING bm25 (id, bm25_terms)"
        )


def drop_bm25(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(f"DROP INDEX IF EXISTS {BM25_INDEX}")


class Migration(migrations.Migration):
    dependencies = [
        ("knowledge", "0011_chunk_embedding"),
    ]

    operations = [
        migrations.AddField(
            model_name="knowledgechunk",
            name="bm25_terms",
            field=models.TextField(editable=False, null=True),
        ),
        migrations.RunPython(enable_bm25, drop_bm25),
    ]
