# qa_app/utils.py
from __future__ import annotations

from typing import Optional, Tuple
from asgiref.sync import sync_to_async
from django.conf import settings
from pgvector.django import CosineDistance

from qa_app.models import QAEntry
from qa_app.services.embeddings import embed_text_async

TOP_K = getattr(settings, "SEARCH_TOP_K", 5)
SIM_THRESHOLD = getattr(settings, "SEARCH_SIM_THRESHOLD", 0.35)


def _query_best_sync(q_vec) -> Optional[tuple[QAEntry, float]]:
    """
    Аннотуємо cosine distance; беремо найменшу дистанцію.
    Схожість рахуємо як (1 - distance). Очікуваний діапазон ~[0..1].
    """
    qs = (
        QAEntry.objects
        .exclude(embedding__isnull=True)
        .annotate(distance=CosineDistance("embedding", q_vec))
        .order_by("distance")
        .only("id", "answer")
    )
    best = qs.first()
    if not best:
        return None

    dist = float(getattr(best, "distance", 1.0))
    similarity = 1.0 - dist
    return best, similarity


async def find_best_match(question: str) -> Tuple[Optional[QAEntry], Optional[float]]:
    """
    Отримуємо embedding асинхронно, шукаємо найближчий запис.
    Фільтруємо по порогу SIM_THRESHOLD.
    """
    q_vec = await embed_text_async(question)
    if not q_vec:
        return None, None

    result = await sync_to_async(_query_best_sync)(q_vec)
    if not result:
        return None, None

    obj, sim = result
    if sim is None or sim < SIM_THRESHOLD:
        return None, sim
    return obj, sim
