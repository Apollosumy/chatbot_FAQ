from django.contrib import admin
from .models import InstructionCategory, InstructionSubcategory, Instruction, Tag
from audittrail.admin_mixins import AuditedModelAdmin


@admin.register(InstructionCategory)
class InstructionCategoryAdmin(AuditedModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(InstructionSubcategory)
class InstructionSubcategoryAdmin(AuditedModelAdmin):
    list_display = ('name', 'category')
    list_filter = ('category',)
    search_fields = ('name',)


@admin.register(Instruction)
class InstructionAdmin(AuditedModelAdmin):
    list_display = ('title', 'subcategory')
    list_filter = ('subcategory',)
    search_fields = ('title', 'content')
    filter_horizontal = ('tags',)


@admin.register(Tag)
class TagAdmin(AuditedModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
