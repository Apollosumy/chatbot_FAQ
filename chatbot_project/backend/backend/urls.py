from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse, HttpResponseNotFound
from backend.core.security import require_api_key
from backend.core.auth import require_telegram_access
import hashlib
from django.views.generic import RedirectView


# ----- допоміжна функція для маскування секретів -----
def _mask(v: str | None, keep=4):
    if not v:
        return v
    return v[:keep] + "…" + v[-keep:] if len(v) > keep * 2 else "****"

# ----- сервісний ping -----
@require_api_key
@require_telegram_access
async def ping(request):
    try:
        body = await request.body
    except TypeError:
        body = request.body
    return JsonResponse({
        "method": request.method,
        "full_path": request.get_full_path(),
        "headers_seen": {
            "X-API-Key": _mask(request.headers.get("X-API-Key")),
            "X-Timestamp": request.headers.get("X-Timestamp"),
            "X-Signature": _mask(request.headers.get("X-Signature")),
            "X-Content-SHA256": _mask(request.headers.get("X-Content-SHA256")),
            "X-Telegram-Id": request.headers.get("X-Telegram-Id"),
        },
        "body_sha256": hashlib.sha256(body or b"").hexdigest(),
    })

# ----- нестандартний шлях до адмінки -----
CUSTOM_ADMIN_PATH = "super-admin-42/"

urlpatterns = [
    # важливо: немає стандартного "admin/", замість нього наш шлях
    path(CUSTOM_ADMIN_PATH, admin.site.urls),

    # (необов’язково) заховаємо /admin/ під 404, щоб не світився дефолтний URL
    path("admin/", lambda request: HttpResponseNotFound()),

    # API
    path("api/ping/", ping),
    path("api/", include("qa_app.urls")),
    path("api/", include("instructions_app.urls")),
    path("api/", include("feedback_app.urls")),
    path("", RedirectView.as_view(url="/super-admin-42/", permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
