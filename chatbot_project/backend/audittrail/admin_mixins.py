from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from .models import AuditLog, AuditAction
from .audit import model_diff

class AuditedModelAdmin(admin.ModelAdmin):
    audit_include_fields = None
    audit_exclude_fields = ("id", )

    def log_audit(self, request, obj, action, description="", changes=None):
        """
        Уніфікований запис аудиту.
        request може бути None (наприклад виклики зі скриптів) — тоді actor буде None.
        """
        try:
            actor = None
            if request is not None:
                actor = getattr(request, "user", None)
            AuditLog.objects.create(
                actor=actor,
                action=action,
                content_type=ContentType.objects.get_for_model(obj.__class__),
                object_id=str(getattr(obj, "pk", "")),
                description=description or "",
                changes=changes or {},
            )
        except Exception:
            # Навіть якщо запис аудиту не вдасться — не ламаємо основну операцію
            # (логгер тут можна додати при потребі)
            pass

    def save_model(self, request, obj, form, change):
        old_instance = None
        if change:
            try:
                old_instance = obj.__class__.objects.get(pk=obj.pk)
            except obj.__class__.DoesNotExist:
                old_instance = None

        super().save_model(request, obj, form, change)

        if change:
            changes = model_diff(
                old_instance, obj,
                include_fields=self.audit_include_fields,
                exclude_fields=self.audit_exclude_fields
            )
            # Запис оновлення
            self.log_audit(
                request,
                obj,
                AuditAction.UPDATE,
                description=f"Оновлено {obj._meta.verbose_name} «{obj}»",
                changes=changes or {}
            )
        else:
            # Запис створення
            self.log_audit(
                request,
                obj,
                AuditAction.CREATE,
                description=f"Створено {obj._meta.verbose_name} «{obj}»",
                changes=model_diff(None, obj,
                                   include_fields=self.audit_include_fields,
                                   exclude_fields=self.audit_exclude_fields)
            )

    def delete_model(self, request, obj):
        # Логуємо перед фактичним видаленням, щоб зберегти content_object info
        try:
            self.log_audit(
                request,
                obj,
                AuditAction.DELETE,
                description=f"Видалено {obj._meta.verbose_name} «{obj}»",
            )
        except Exception:
            pass
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        """
        Обробка bulk delete з changelist. Django звично викликає саме цей метод
        під час action 'delete selected'. Тут логуватимемо кожен об'єкт окремо.
        """
        # Перебираємо queryset по одному, щоб логувати кожен об'єкт
        for obj in queryset:
            try:
                self.log_audit(
                    request,
                    obj,
                    AuditAction.DELETE,
                    description=f"Видалено {obj._meta.verbose_name} «{obj}» (bulk)"
                )
            except Exception:
                # не зупиняємо операцію через помилку логування
                pass
        super().delete_queryset(request, queryset)
