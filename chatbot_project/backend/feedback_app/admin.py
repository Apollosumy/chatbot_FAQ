from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from audittrail.models import AuditLog, AuditAction
from .models import BotFeedback


@admin.register(BotFeedback)
class BotFeedbackAdmin(admin.ModelAdmin):
    list_display = ("submitted_at", "is_resolved", "short_message")
    list_filter = ("is_resolved",)
    search_fields = ("message",)
    actions = ["mark_resolved"]

    def short_message(self, obj):
        return obj.message[:60] + "..." if len(obj.message) > 60 else obj.message

    def mark_resolved(self, request, queryset):
        updated = queryset.update(is_resolved=True)
        for obj in queryset:
            if obj.is_resolved:  # позначено як оброблене
                AuditLog.objects.create(
                    actor=getattr(request, "user", None),
                    action=AuditAction.ERROR_PROCESSED,
                    content_type=ContentType.objects.get_for_model(BotFeedback),
                    object_id=str(obj.pk),
                    description=f"Оброблено повідомлення про помилку #{obj.pk}",
                    changes={"is_resolved": {"old": False, "new": True}},
                )
        self.message_user(request, f"Оновлено: {updated}")
    mark_resolved.short_description = "Позначити як оброблені"
