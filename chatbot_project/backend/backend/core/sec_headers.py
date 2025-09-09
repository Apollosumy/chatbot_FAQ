from __future__ import annotations
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Додає безпечні заголовки. CSP у DEBUG працює як Report-Only,
    щоби нічого не ламати під час розробки.
    """

    def process_response(self, request, response):
        # Мінімізує MIME sniffing
        response.headers.setdefault("X-Content-Type-Options", "nosniff")

        # Обмежує, хто може вбудовувати наш сайт у <iframe>
        # (X-Frame-Options дублюється стандартним middleware — залишаємо для сумісності)
        response.headers.setdefault("X-Frame-Options", "DENY")

        # Політика реферера: не віддавати повний URL на інші сайти
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")

        # Вимикаємо небажані браузерні можливості (корисно проти data exfiltration)
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=(), payment=(), usb=(), magnetometer=(), gyroscope=()"
        )

        # Content-Security-Policy: базова, достатньо лояльна для Django Admin.
        csp = (
            "default-src 'self'; "
            "img-src 'self' data: blob:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        )

        if settings.DEBUG:
            # У дебазі — лише сповіщення (не блокує), щоб бачити порушення в консолі
            response.headers.setdefault("Content-Security-Policy-Report-Only", csp)
        else:
            response.headers.setdefault("Content-Security-Policy", csp)

        return response
