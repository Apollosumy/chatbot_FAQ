# backend/core/hmac_auth.py
import time
import hmac
import hashlib
from django.conf import settings
from django.http import HttpResponse


def _bad(reason: str, status=401):
    # Прозоро пояснюємо причину у DEBUG, у проді — мінімум деталей.
    if settings.DEBUG:
        return HttpResponse(f"Unauthorized: {reason}", status=status)
    return HttpResponse("Unauthorized", status=status)


class HMACAuthMiddleware:
    """
    Перевіряє для всіх шляхів, що починаються з /api/:
      1) X-API-Key == settings.DJANGO_API_KEY
      2) X-Timestamp у межах TTL
      3) X-Signature (HMAC-SHA256) правильний
         для рядка: "<ts>\n<METHOD>\n<full_path>\n<sha256(body)>"
      4) (необов'язково) X-Content-SHA256 збігається з реальним body hash
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.api_key = getattr(settings, "DJANGO_API_KEY", "")
        self.hmac_secret = getattr(settings, "DJANGO_HMAC_SECRET", "")
        self.ttl = int(getattr(settings, "DJANGO_HMAC_TTL", 120))

    def __call__(self, request):
        # Захищаємо тільки API-ендпоїнти
        if not request.path.startswith("/api/"):
            return self.get_response(request)

        # 1) API key
        api_key = request.headers.get("X-API-Key", "")
        if not self.api_key or api_key != self.api_key:
            return _bad("bad api key")

        # 2) Timestamp
        ts = request.headers.get("X-Timestamp")
        if not ts:
            return _bad("missing timestamp")

        try:
            ts_int = int(ts)
        except ValueError:
            return _bad("invalid timestamp")

        now = int(time.time())
        if abs(now - ts_int) > self.ttl:
            return _bad("stale timestamp/replay")

        # 3) Обчислюємо реальний hash body
        body_bytes = request.body  # Django кешує, безпечно читати
        body_sha256 = hashlib.sha256(body_bytes).hexdigest()

        # якщо клієнт надіслав X-Content-SHA256 — звіримося
        content_hdr = request.headers.get("X-Content-SHA256")
        if content_hdr and content_hdr != body_sha256:
            return _bad("mismatched body hash")

        method = request.method.upper()
        # ВАЖЛИВО: підписуємо full_path (шлях + query), а не лише шлях
        full_path = request.get_full_path()

        to_sign = "\n".join([ts, method, full_path, body_sha256]).encode("utf-8")
        expected = hmac.new(
            self.hmac_secret.encode("utf-8"),
            to_sign,
            hashlib.sha256
        ).hexdigest()

        sig = request.headers.get("X-Signature", "")
        # приймаємо як "v1=<hex>", так і чистий hex
        if sig.startswith("v1="):
            sig = sig[3:]

        if not hmac.compare_digest(expected, sig):
            return _bad("bad signature")

        # все гаразд
        return self.get_response(request)
