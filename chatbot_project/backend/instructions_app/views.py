import json
from asgiref.sync import sync_to_async
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import InstructionNode, Instruction
from backend.core.security import require_api_key
from backend.core.auth import require_telegram_access


@csrf_exempt
@require_api_key
@require_telegram_access
async def get_categories(request):
    """
    Повертає "категорії" — всі кореневі вузли дерева (parent is null).
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    qs = InstructionNode.objects.filter(parent__isnull=True).order_by("name")
    data = [{"id": c.id, "name": c.name} async for c in qs]
    return JsonResponse(data, safe=False)


@csrf_exempt
@require_api_key
@require_telegram_access
async def get_subcategories(request, category_id: int):
    """
    Повертає "підкатегорії" — дочірні вузли для переданого вузла (будь-якого рівня).
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    qs = InstructionNode.objects.filter(parent_id=category_id).order_by("name")
    data = [{"id": s.id, "name": s.name} async for s in qs]
    return JsonResponse(data, safe=False)


@csrf_exempt
@require_api_key
@require_telegram_access
async def get_instructions(request, subcategory_id: int):
    """
    Повертає інструкції, привʼязані до конкретного вузла дерева (будь-якого рівня).
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    qs = Instruction.objects.filter(node_id=subcategory_id).order_by("title")
    data = [{"id": i.id, "title": i.title} async for i in qs]
    return JsonResponse(data, safe=False)


@csrf_exempt
@require_api_key
@require_telegram_access
async def search_instructions(request):
    """
    Пошук інструкцій за назвою, текстом і тегами.
    query параметр: ?query=...
    """
    query = request.GET.get("query", "").strip()
    if not query:
        return JsonResponse([], safe=False)

    instructions = await sync_to_async(list)(
        Instruction.objects.filter(
            Q(title__icontains=query)
            | Q(content__icontains=query)
            | Q(tags__name__icontains=query)
        )
        .distinct()
        .values("id", "title")
    )
    return JsonResponse(instructions, safe=False)


@csrf_exempt
@require_api_key
@require_telegram_access
async def get_instruction_detail(request, instruction_id: int):
    """
    Деталі однієї інструкції.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        instruction = await Instruction.objects.aget(id=instruction_id)
    except Instruction.DoesNotExist:
        return JsonResponse({"error": "Instruction not found"}, status=404)

    data = {
        "title": instruction.title,
        "content": instruction.content,
        "image_url": instruction.image.url if instruction.image else None,
    }
    return JsonResponse(data)
