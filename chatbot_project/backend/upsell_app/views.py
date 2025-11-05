from __future__ import annotations

from django.db import models
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import CrossItem, ChangeSaleItem, AccessoryCategory
from .serializers import (
    AccessoryCategorySerializer,
    AccessoryCategoryTextSerializer,
    ChangeSearchResultSerializer,
)

# Доступ контролюється HMAC + whitelist middleware на всіх /api/**
# Тому тут AllowAny: додаткові DRF-permissions не потрібні.

# ---------- КРОСС: один текст ----------
@api_view(["GET"])
@permission_classes([AllowAny])
def cross_text(request):
    """Повертає текст для розділу 'Кросс' (беремо перший активний запис)."""
    obj = CrossItem.objects.filter(is_active=True).order_by("id").first()
    text = (obj.instruction_text or "").strip() if obj else ""
    return Response({"text": text})


# ---------- АКСЕСУАРИ: список категорій ----------
@api_view(["GET"])
@permission_classes([AllowAny])
def accessories_categories(request):
    objs = AccessoryCategory.objects.all().order_by("name")
    data = AccessoryCategorySerializer(objs, many=True).data
    return Response(data)


# ---------- АКСЕСУАРИ: текст категорії ----------
@api_view(["GET"])
@permission_classes([AllowAny])
def accessories_category_text(request, category_id: int):
    obj = AccessoryCategory.objects.filter(id=category_id).first()
    if not obj:
        return Response({"detail": "Not found"}, status=404)
    data = AccessoryCategoryTextSerializer(obj).data
    return Response(data)


# ---------- CHANGE: пошук по артикулу/коду ----------
@api_view(["GET"])
@permission_classes([AllowAny])
def change_search(request):
    """
    GET /api/upsell/change/search/?q=<article_or_code>
    Пошук у ChangeSaleItem за article/code (iexact або icontains). Повертає перший збіг.
    """
    q = (request.GET.get("q") or "").strip()
    if not q:
        return Response({"detail": "q required"}, status=400)

    qs = ChangeSaleItem.objects.filter(is_active=True).filter(
        models.Q(article__iexact=q) |
        models.Q(code__iexact=q) |
        models.Q(article__icontains=q) |
        models.Q(code__icontains=q)
    ).order_by("id")

    obj = qs.first()
    if not obj:
        return Response({"detail": "Not found"}, status=404)

    data = ChangeSearchResultSerializer(obj).data
    return Response(data)
