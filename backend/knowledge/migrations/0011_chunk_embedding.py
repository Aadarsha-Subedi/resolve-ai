import pgvector.django.vector
from django.db import migrations, models
from pgvector.django import HnswIndex

from common.db.operations import AddPostgresIndex


class Migration(migrations.Migration):
    dependencies = [
        ("knowledge", "0010_chunk_upload_source"),
    ]

    operations = [
        migrations.AddField(
            model_name="knowledgechunk",
            name="embedding",
            field=pgvector.django.vector.VectorField(
                dimensions=768, editable=False, null=True
            ),
        ),
        migrations.AddField(
            model_name="knowledgechunk",
            name="embedding_model",
            field=models.CharField(blank=True, default="", max_length=60),
        ),
        AddPostgresIndex(
            model_name="knowledgechunk",
            index=HnswIndex(
                ef_construction=64,
                fields=["embedding"],
                m=16,
                name="knowledge_chunk_embedding_hnsw",
                opclasses=["vector_cosine_ops"],
            ),
        ),
    ]
