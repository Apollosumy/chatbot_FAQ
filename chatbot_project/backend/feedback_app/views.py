import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import BotFeedback
from backend.core.security import require_api_key
from backend.core.auth import require_telegram_access

logger = logging.getLogger(__name__)


@csrf_exempt
@require_api_key
@require_telegram_access
async def submit_feedback(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError as e:
        logger.error(f"Помилка декодування JSON: {str(e)}")
        return JsonResponse({'error': 'Некоректний JSON'}, status=400)

    message = (payload.get('message') or '').strip()
    user_id = (payload.get('user_id') or '').strip() or None

    if not message:
        logger.warning("Поле 'message' не заповнене або порожнє.")
        return JsonResponse({'error': 'Поле "message" не може бути порожнім.'}, status=400)

    try:
        await BotFeedback.objects.acreate(message=message, user_id=user_id)
        logger.info("Відгук збережено")
        return JsonResponse({'status': 'OK'}, status=201)
    except Exception as e:
        logger.error(f"Помилка збереження відгуку: {str(e)}")
        return JsonResponse({'error': 'Помилка збереження даних'}, status=500)
