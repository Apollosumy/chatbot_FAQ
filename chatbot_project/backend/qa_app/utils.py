from __future__ import annotations

from typing import Optional, Tuple
from asgiref.sync import sync_to_async
from django.conf import settings
from pgvector.django import CosineDistance

from qa_app.models import QAEntry, QAVariant
from qa_app.services.embeddings import embed_text_async
from qa_app.text_utils import normalize_text

TOP_K = getattr(settings, "SEARCH_TOP_K", 5)
SIM_THRESHOLD = getattr(settings, "SEARCH_SIM_THRESHOLD", 0.35)


def _query_best_sync(q_vec) -> Optional[tuple[QAEntry, float]]:
    """
    Шукаємо по QAVariant (питання + кожен синонім має власний embedding).
    Беремо мінімальну cosine distance та повертаємо (entry, similarity).
    """
    qs = (
        QAVariant.objects
        .exclude(embedding__isnull=True)
        .annotate(distance=CosineDistance("embedding", q_vec))
        .select_related("entry")
        .order_by("distance")
        .only("id", "entry_id", "text")
    )
    best = qs.first()
    if not best:
        return None

    dist = float(getattr(best, "distance", 1.0))
    similarity = 1.0 - dist
    return best.entry, similarity


async def find_best_match(question: str) -> Tuple[Optional[QAEntry], Optional[float]]:
    """
    Отримуємо embedding запиту та шукаємо найближчий варіант.
    Фільтр по порогу SIM_THRESHOLD.

    Важливо: перед побудовою ембедінга нормалізуємо текст (lowercase, видалення зайвої пунктуації),
    щоб пошук був нечутливий до регістру та простих варіацій написання.
    """
    norm_q = normalize_text(question)
    q_vec = await embed_text_async(norm_q)
    if not q_vec:
        return None, None

    result = await sync_to_async(_query_best_sync)(q_vec)
    if not result:
        return None, None

    entry, sim = result
    if sim is None or sim < SIM_THRESHOLD:
        return None, sim
    return entry, sim
