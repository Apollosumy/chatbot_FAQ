from __future__ import annotations
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.db.models import JSONField

User = get_user_model()

class AuditAction(models.TextChoices):
    CREATE = "create", "Створення"
    UPDATE = "update", "Редагування"
    DELETE = "delete", "Видалення"
    ERROR_PROCESSED = "error_processed", "Обробка повідомлення про помилку"

class AuditLog(models.Model):
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    actor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs")
    action = models.CharField(max_length=32, choices=AuditAction.choices)

    # Об'єкт зміни
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=64)
    content_object = GenericForeignKey("content_type", "object_id")

    # Опис і diff
    description = models.TextField(blank=True, default="")
    changes = JSONField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["timestamp"]),
            models.Index(fields=["action"]),
            models.Index(fields=["content_type", "object_id"]),
        ]
        ordering = ["-timestamp"]
        verbose_name = "Запис аудиту"
        verbose_name_plural = "Записи аудиту"

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.get_action_display()} {self.content_type}:{self.object_id}"
