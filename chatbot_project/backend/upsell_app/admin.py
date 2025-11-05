from __future__ import annotations
from django.contrib import admin
from .models import CrossItem, ChangeSaleItem, AccessoryCategory, Accessory


@admin.register(CrossItem)
class CrossItemAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("title", "short_note", "instruction_text")
    ordering = ("title",)


@admin.register(ChangeSaleItem)
class ChangeSaleItemAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("title", "short_note", "instruction_text")
    ordering = ("title",)


class AccessoryInline(admin.TabularInline):
    model = Accessory
    extra = 0
    fields = ("title", "is_active", "short_note")
    show_change_link = True


@admin.register(AccessoryCategory)
class AccessoryCategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    inlines = [AccessoryInline]


@admin.register(Accessory)
class AccessoryAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_active", "created_at")
    list_filter = ("category", "is_active")
    search_fields = ("title", "short_note", "instruction_text")
    ordering = ("title",)
