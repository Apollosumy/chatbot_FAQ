import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import UnansweredQuestion, QuestionLog
from .utils import find_best_match
from backend.core.security import require_api_key
from backend.core.auth import require_telegram_access


@csrf_exempt
@require_api_key
@require_telegram_access
async def search_answer(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    question = (data.get("question") or "").strip()
    if not question:
        return JsonResponse({"error": "Field 'question' is required"}, status=400)

    entry, similarity = await find_best_match(question)

    if entry:
        await QuestionLog.objects.acreate(
            question=question, answer_found=True, similarity=float(round(similarity, 6))
        )
        return JsonResponse({
            "answer": entry.answer,
            "similarity": round(float(similarity), 4)
        })

    if len(question.split()) >= 3:
        exists = await UnansweredQuestion.objects.filter(question=question).aexists()
        if not exists:
            await UnansweredQuestion.objects.acreate(question=question)

    await QuestionLog.objects.acreate(
        question=question, answer_found=False, similarity=float(round((similarity or 0.0), 6))
    )

    return JsonResponse({
        "answer": "Вибачте, відповідь на Ваше питання не знайдена. Я передаю його для обробки адміністратору."
    }, status=404)
