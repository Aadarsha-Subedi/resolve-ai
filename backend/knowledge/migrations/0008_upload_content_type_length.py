from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("knowledge", "0007_enable_pgvector")]

    operations = [
        migrations.AlterField(
            model_name="knowledgeupload",
            name="content_type",
            field=models.CharField(max_length=100),
        ),
    ]
