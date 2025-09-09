from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ("qa_app", "0000_enable_pgvector"),
        ("qa_app", "0007_alter_qaentry_embedding"),
    ]
    operations = []
