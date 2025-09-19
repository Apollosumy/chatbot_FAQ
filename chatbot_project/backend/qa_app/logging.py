from typing import Optional
from django.http import HttpRequest
from .models import QuestionLog, AllowedTelegramUser

def log_question_from_request(
    request: HttpRequest,
    *,
    question: str,
    answer_found: bool,
    similarity: Optional[float] = None,
) -> None:
    """
    Створює QuestionLog і, якщо можливо, підв’язує asked_by за X-Telegram-Id.
    Використовуй у view після обчислення відповіді/схожості.
    """
    tg_id_header = request.headers.get("X-Telegram-Id")
    asked_by = None
    if tg_id_header:
        try:
            tg_id = int(tg_id_header)
            asked_by = AllowedTelegramUser.objects.filter(user_id=tg_id).first()
        except (TypeError, ValueError):
            asked_by = None

    QuestionLog.objects.create(
        question=question,
        answer_found=answer_found,
        similarity=similarity,
        asked_by=asked_by,
    )
