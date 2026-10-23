from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("knowledge", "0008_upload_content_type_length")]

    operations = [
        migrations.AddField(
            model_name="knowledgeupload",
            name="index_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("indexing", "Indexing"),
                    ("indexed", "Indexed"),
                    ("failed", "Failed"),
                ],
                default="pending",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="knowledgeupload",
            name="index_error",
            field=models.CharField(blank=True, default="", max_length=40),
        ),
        migrations.AddField(
            model_name="knowledgeupload",
            name="indexed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="knowledgeupload",
            name="extracted_key",
            field=models.CharField(blank=True, default="", max_length=300),
        ),
        migrations.AddField(
            model_name="knowledgeupload",
            name="page_count",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
