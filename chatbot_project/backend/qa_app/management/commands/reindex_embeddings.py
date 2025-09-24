from django.core.management.base import BaseCommand
from qa_app.models import QAEntry

class Command(BaseCommand):
    help = "Recompute embeddings for all QAEntry and their QAVariants using normalized text."

    def handle(self, *args, **options):
        qs = QAEntry.objects.all()
        total = qs.count()
        self.stdout.write(f"Reindexing {total} entries...")
        for i, entry in enumerate(qs, start=1):
            # викликаємо save() — в ньому зараз перегенерується embedding і QAVariant
            entry.save()
            if i % 50 == 0:
                self.stdout.write(f"{i}/{total} done")
        self.stdout.write("Done.")
