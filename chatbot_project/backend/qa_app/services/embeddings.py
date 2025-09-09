import os
from typing import List
from openai import OpenAI
import asyncio

# ЧИТАЄМО ЛИШЕ ЦІ ДВІ ЗМІННІ
OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
EMBED_DIM = int(os.getenv("EMBED_DIMENSIONS", "1536"))

_client = OpenAI()

def embed_text_sync(text: str) -> List[float]:
    """
    Повертає вектор рівно EMBED_DIM елементів (обрізка/доповнення нулями за потреби).
    """
    text = (text or "").strip()
    if not text:
        return [0.0] * EMBED_DIM

    resp = _client.embeddings.create(model=OPENAI_EMBED_MODEL, input=text)
    vec = resp.data[0].embedding

    # Нормалізуємо довжину під розмір колонки vector(EMBED_DIM)
    if len(vec) > EMBED_DIM:
        vec = vec[:EMBED_DIM]
    elif len(vec) < EMBED_DIM:
        vec = vec + [0.0] * (EMBED_DIM - len(vec))
    return vec

async def embed_text_async(texts):
    """
    Async-обгортка над embed_text_sync, щоб не ламати існуючі імпорти.
    Виконуємо синхронний розрахунок у thread-пулі.
    """
    return await asyncio.to_thread(embed_text_sync, texts)
