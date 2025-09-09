# backend/core/security.py
import os
import time
import hmac
import hashlib
import logging
from functools import wraps
from django.http import JsonResponse

logger = logging.getLogger(__name__)

DJANGO_API_KEY = os.getenv("DJANGO_API_KEY", "")
DJANGO_HMAC_SECRET = os.getenv("DJANGO_HMAC_SECRET", "")
DJANGO_HMAC_TTL = int(os.getenv("DJANGO_HMAC_TTL", "120"))  # сек

def _unauth(msg: str, extra: dict | None = None):
    payload = {"error": "unauthorized", "detail": msg}
    if extra:
        payload["debug"] = extra
    logger.warning(f"AUTH FAIL: {msg} | {extra or {}}")
    return JsonResponse(payload, status=401)

def _auth_ok(msg: str, extra: dict | None = None):
    logger.info(f"AUTH PASS: {msg} | {extra or {}}")

def _get_header(request, name: str) -> str | None:
    return request.headers.get(name)

async def _read_body(request):
    try:
        body = await request.body
    except TypeError:
        body = request.body
    return body or b""

def _calc_sig(ts: str, method: str, full_path: str, body_bytes: bytes, secret: str) -> tuple[str, str]:
    content_hash = hashlib.sha256(body_bytes).hexdigest()
    to_sign = "\n".join([ts, method.upper(), full_path, content_hash]).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), to_sign, hashlib.sha256).hexdigest()
    return content_hash, sig

async def _verify_hmac(request):
    ts = _get_header(request, "X-Timestamp")
    sig_hdr = _get_header(request, "X-Signature")
    body_sha_hdr = _get_header(request, "X-Content-SHA256")

    if not (ts and sig_hdr and body_sha_hdr):
        return _unauth("missing hmac headers", {"need": ["X-Timestamp", "X-Signature", "X-Content-SHA256"]})

    try:
        ts_int = int(ts)
    except ValueError:
        return _unauth("bad timestamp")

    now = int(time.time())
    if abs(now - ts_int) > DJANGO_HMAC_TTL:
        return _unauth("timestamp expired", {"now": now, "ts": ts_int, "ttl": DJANGO_HMAC_TTL})

    method = request.method
    full_path = request.get_full_path()
    body = await _read_body(request)

    calc_body_sha, calc_sig = _calc_sig(ts, method, full_path, body, DJANGO_HMAC_SECRET)

    if not hmac.compare_digest(calc_body_sha, body_sha_hdr):
        return _unauth("bad body sha256", {
            "expected": calc_body_sha,
            "got": body_sha_hdr,
            "method": method,
            "full_path": full_path,
            "body_len": len(body),
        })

    if not sig_hdr.startswith("v1="):
        return _unauth("bad signature format")
    got_sig = sig_hdr.split("=", 1)[1]

    if not hmac.compare_digest(calc_sig, got_sig):
        return _unauth("bad signature", {
            "expected_sig": calc_sig,
            "got_sig": got_sig,
            "method": method,
            "full_path": full_path,
            "body_sha256": calc_body_sha,
        })

    _auth_ok("hmac ok", {"method": method, "path": full_path})
    return None

def require_hmac(view_func):
    """Чистий HMAC-чек (без API-ключа)."""
    @wraps(view_func)
    async def _wrapped(request, *args, **kwargs):
        err = await _verify_hmac(request)
        if err:
            return err
        return await view_func(request, *args, **kwargs)
    return _wrapped

def require_api_key(view_func):
    """API-ключ + HMAC."""
    @wraps(view_func)
    async def _wrapped(request, *args, **kwargs):
        api_key = _get_header(request, "X-API-Key")
        if not api_key or api_key != DJANGO_API_KEY:
            return _unauth("invalid api key")

        err = await _verify_hmac(request)
        if err:
            return err

        return await view_func(request, *args, **kwargs)
    return _wrapped
