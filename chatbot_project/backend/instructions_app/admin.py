from django.contrib import admin
from .models import InstructionNode, Instruction, Tag
from audittrail.admin_mixins import AuditedModelAdmin


@admin.register(InstructionNode)
class InstructionNodeAdmin(AuditedModelAdmin):
    list_display = ("name", "parent", "is_root")
    list_filter = ("parent",)
    search_fields = ("name",)
    ordering = ("parent_id", "name")


@admin.register(Instruction)
class InstructionAdmin(AuditedModelAdmin):
    list_display = ("title", "node")
    list_filter = ("node", "tags")
    search_fields = ("title", "content")
    filter_horizontal = ("tags",)


@admin.register(Tag)
class TagAdmin(AuditedModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
