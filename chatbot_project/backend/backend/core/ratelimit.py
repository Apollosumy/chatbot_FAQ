# backend/core/ratelimit.py
import time
import logging
from django.http import JsonResponse

logger = logging.getLogger(__name__)

# 1 запит / 10 секунд
RATE_LIMIT_SECONDS = 10

# Лімітуємо лише ці шляхи (і лише для зазначених методів)
LIMITED_PATHS = {
    ("/api/search/", frozenset({"POST"})),
    ("/api/feedback/", frozenset({"POST"})),
}

# Виключення (не лімітуємо)
EXCLUDED_PATHS = {
    "/api/ping/",
}

# Пам’ять у процесі: {(key, path): last_ts}
_last_request: dict[tuple[str, str], float] = {}


def _rate_limit_applies(path: str, method: str) -> bool:
    if path in EXCLUDED_PATHS:
        return False
    for limited_path, methods in LIMITED_PATHS:
        if path == limited_path and method.upper() in methods:
            return True
    return False


class RateLimitMiddleware:
    """
    Синхронний middleware з лімітом “1 запит / 10 сек” на користувача і шлях.
    Ключ користувача: X-Telegram-Id, а якщо немає — REMOTE_ADDR.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        method = request.method.upper()

        if not _rate_limit_applies(path, method):
            return self.get_response(request)

        user_id = request.headers.get("X-Telegram-Id")
        if not user_id:
            user_id = request.META.get("REMOTE_ADDR", "anonymous")

        now = time.monotonic()
        key = (str(user_id), path)
        last = _last_request.get(key, 0.0)
        delta = now - last

        if delta < RATE_LIMIT_SECONDS:
            retry_after = max(int(RATE_LIMIT_SECONDS - delta), 1)
            logger.warning(f"Rate limit exceeded for user={user_id} path={path}")
            resp = JsonResponse(
                {
                    "error": "too_many_requests",
                    "detail": f"Дочекайтеся {retry_after} сек перед новим запитом",
                },
                status=429,
            )
            resp["Retry-After"] = str(retry_after)
            return resp

        _last_request[key] = now
        return self.get_response(request)
