from __future__ import annotations

from typing import List, Tuple
from django.db import connection

def pg_cosine_topk(query_vector: List[float], top_k: int = 5) -> list[Tuple]:
    """
    Прямий пошук у Postgres з pgvector: повертає (id, question, answer, cosine_distance).
    """
    if not query_vector:
        return []

    vector_str = "[" + ",".join(f"{float(x):.8f}" for x in query_vector) + "]"

    sql = """
        SELECT id, question, answer,
               embedding <#> %s::vector AS cosine_distance
        FROM qa_app_qaentry
        ORDER BY cosine_distance ASC
        LIMIT %s
    """

    with connection.cursor() as cur:
        cur.execute(sql, [vector_str, top_k])
        return cur.fetchall()
