from django.db import migrations

class Migration(migrations.Migration):
    initial = False
    dependencies = []
    operations = [
        migrations.RunSQL("CREATE EXTENSION IF NOT EXISTS vector;")
    ]
