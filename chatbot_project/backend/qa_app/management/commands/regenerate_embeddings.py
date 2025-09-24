from django.core.management.base import BaseCommand
from django.db import transaction
from qa_app.models import QAEntry, QAVariant
from qa_app.text_utils import normalize_text
from qa_app.services.embeddings import embed_text_sync

class Command(BaseCommand):
    help = "Rebuild embeddings for all QAEntry and QAVariant using normalized text."

    def handle(self, *args, **options):
        qs = QAEntry.objects.all()
        total = qs.count()
        self.stdout.write(f"Will process {total} entries...")
        i = 0
        for entry in qs.iterator():
            i += 1
            self.stdout.write(f"[{i}/{total}] entry id={entry.pk} - {entry.question!r} ...", ending=" ")
            try:
                with transaction.atomic():
                    # нормалізуємо головне питання і робимо embedding
                    q = (entry.question or "").strip()
                    norm_q = normalize_text(q)
                    emb = embed_text_sync(norm_q) if q else None

                    # ОНОВЛЕННЯ QAEntry.embedding через queryset.update() щоб уникнути повторного виклику save()
                    QAEntry.objects.filter(pk=entry.pk).update(embedding=emb)

                    # Перегенеруємо варіанти
                    QAVariant.objects.filter(entry=entry).delete()
                    for text in entry.get_variants_list():
                        norm_text = normalize_text(text)
                        vec = embed_text_sync(norm_text)
                        QAVariant.objects.create(entry=entry, text=text, embedding=vec)
                self.stdout.write(self.style.SUCCESS("OK"))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"FAILED: {exc}"))
        self.stdout.write(self.style.SUCCESS("All done."))
