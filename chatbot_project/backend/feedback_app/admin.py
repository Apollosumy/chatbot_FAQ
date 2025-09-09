from django.contrib import admin
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
        queryset.update(is_resolved=True)
    mark_resolved.short_description = "Позначити як оброблені"
