import json
from asgiref.sync import sync_to_async
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import InstructionCategory, InstructionSubcategory, Instruction
from backend.core.security import require_api_key
from backend.core.auth import require_telegram_access


@csrf_exempt
@require_api_key
@require_telegram_access
async def get_categories(request):
    if request.method != 'GET':
        return JsonResponse({"error": "Method not allowed"}, status=405)

    categories = InstructionCategory.objects.all()
    data = [{"id": c.id, "name": c.name} async for c in categories]
    return JsonResponse(data, safe=False)


@csrf_exempt
@require_api_key
@require_telegram_access
async def get_subcategories(request, category_id):
    if request.method != 'GET':
        return JsonResponse({"error": "Method not allowed"}, status=405)

    subcategories = InstructionSubcategory.objects.filter(category_id=category_id)
    data = [{"id": s.id, "name": s.name} async for s in subcategories]
    return JsonResponse(data, safe=False)


@csrf_exempt
@require_api_key
@require_telegram_access
async def get_instructions(request, subcategory_id):
    if request.method != 'GET':
        return JsonResponse({"error": "Method not allowed"}, status=405)

    instructions = Instruction.objects.filter(subcategory_id=subcategory_id)
    data = [{"id": i.id, "title": i.title} async for i in instructions]
    return JsonResponse(data, safe=False)


@csrf_exempt
@require_api_key
@require_telegram_access
async def search_instructions(request):
    query = request.GET.get('query', '').strip()
    if not query:
        return JsonResponse([], safe=False)

    instructions = await sync_to_async(list)(
        Instruction.objects.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query) |
            Q(tags__name__icontains=query)
        ).distinct().values('id', 'title')
    )
    return JsonResponse(instructions, safe=False)


@csrf_exempt
@require_api_key
@require_telegram_access
async def get_instruction_detail(request, instruction_id):
    if request.method != 'GET':
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
