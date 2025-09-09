from django.contrib import admin
from .models import InstructionCategory, InstructionSubcategory, Instruction, Tag

@admin.register(InstructionCategory)
class InstructionCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(InstructionSubcategory)
class InstructionSubcategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    list_filter = ('category',)
    search_fields = ('name',)


@admin.register(Instruction)
class InstructionAdmin(admin.ModelAdmin):
    list_display = ('title', 'subcategory')
    list_filter = ('subcategory',)
    search_fields = ('title', 'content')
    filter_horizontal = ('tags',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
