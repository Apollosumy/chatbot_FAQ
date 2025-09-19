import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import UnansweredQuestion, QuestionLog, AllowedTelegramUser
from .utils import find_best_match
from backend.core.security import require_api_key
from backend.core.auth import require_telegram_access


@csrf_exempt
@require_api_key
@require_telegram_access
async def search_answer(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)

    # --- розпарсимо JSON
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    question = (data.get("question") or "").strip()
    if not question:
        return JsonResponse({"error": "Field 'question' is required"}, status=400)

    # --- хто задав (беремо із заголовка, який уже пройшов require_telegram_access)
    asked_by = None
    tg_header = request.headers.get("X-Telegram-Id")
    if tg_header:
        try:
            uid = int(tg_header)
            # користувач гарантовано існує і активний (перевірено у декораторі),
            # але зробимо захищений пошук на випадок гонок/деактивації
            asked_by = await AllowedTelegramUser.objects.aget(user_id=uid)
        except (ValueError, AllowedTelegramUser.DoesNotExist):
            asked_by = None

    # --- основний пошук
    entry, similarity = await find_best_match(question)

    if entry:
        await QuestionLog.objects.acreate(
            question=question,
            answer_found=True,
            similarity=float(round(similarity, 6)),
            asked_by=asked_by,
        )
        return JsonResponse({
            "answer": entry.answer,
            "similarity": round(float(similarity), 4)
        })

    # якщо не знайшли — зберігаємо питання як "без відповіді" (мінімум 3 слова)
    if len(question.split()) >= 3:
        exists = await UnansweredQuestion.objects.filter(question=question).aexists()
        if not exists:
            await UnansweredQuestion.objects.acreate(question=question)

    await QuestionLog.objects.acreate(
        question=question,
        answer_found=False,
        similarity=float(round((similarity or 0.0), 6)),
        asked_by=asked_by,
    )

    return JsonResponse({
        "answer": "Вибачте, відповідь на Ваше питання не знайдена. Я передаю його для обробки адміністратору."
    }, status=404)
