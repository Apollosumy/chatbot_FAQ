from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from .models import AuditLog, AuditAction
from .audit import model_diff

class AuditedModelAdmin(admin.ModelAdmin):
    """
    Підключи цей міксин замість/разом із ModelAdmin,
    щоб автоматично логувати create/update/delete у AuditLog.
    """
    audit_include_fields = None
    audit_exclude_fields = ("id", )

    def log_audit(self, request, obj, action, description="", changes=None):
        AuditLog.objects.create(
            actor=getattr(request, "user", None),
            action=action,
            content_type=ContentType.objects.get_for_model(obj.__class__),
            object_id=str(obj.pk),
            description=description,
            changes=changes or {},
        )

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
            self.log_audit(
                request,
                obj,
                AuditAction.UPDATE,
                description=f"Оновлено {obj._meta.verbose_name} «{obj}»",
                changes=changes or {}
            )
        else:
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
        # лог до фактичного видалення, щоб мати content_object
        self.log_audit(
            request,
            obj,
            AuditAction.DELETE,
            description=f"Видалено {obj._meta.verbose_name} «{obj}»",
        )
        super().delete_model(request, obj)
