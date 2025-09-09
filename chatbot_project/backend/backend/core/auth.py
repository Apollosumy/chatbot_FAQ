# backend/core/auth.py
import logging
from django.http import JsonResponse
from qa_app.models import AllowedTelegramUser

logger = logging.getLogger("backend.core")

def require_telegram_access(view):
    async def wrapper(request, *args, **kwargs):
        tg_id = request.headers.get("X-Telegram-Id")
        if not tg_id:
            logger.warning("AUTH FAIL: Missing X-Telegram-Id")
            return JsonResponse({"error": "Missing X-Telegram-Id"}, status=403)

        try:
            uid = int(tg_id)
        except ValueError:
            logger.warning("AUTH FAIL: Bad X-Telegram-Id format: %s", tg_id)
            return JsonResponse({"error": "Bad X-Telegram-Id"}, status=403)

        exists = await AllowedTelegramUser.objects.filter(user_id=uid, status=AllowedTelegramUser.Status.ACTIVE).aexists()
        if not exists:
            logger.warning("AUTH FAIL: Telegram ID not allowed: %s", uid)
            return JsonResponse({"error": "Telegram ID not allowed"}, status=403)

        logger.info("AUTH PASS: Telegram ID allowed: %s", uid)
        return await view(request, *args, **kwargs)
    return wrapper
