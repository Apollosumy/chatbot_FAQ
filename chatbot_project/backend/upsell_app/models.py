from __future__ import annotations
from django.db import models


class CrossItem(models.Model):
    title = models.CharField("Назва", max_length=255, db_index=True)
    # short_note = models.TextField(... )  # ← видаляємо з моделі
    instruction_text = models.TextField(
        "Список крос товарів", blank=True,
        help_text="Текст/список, який бот показує для крос-товарів",
    )
    is_active = models.BooleanField("Активний", default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ChangeSaleItem(models.Model):
    """Товари для Change (пошук по артикулу/коду)"""
    title = models.CharField("Назва", max_length=255, db_index=True)
    short_note = models.TextField("Короткий опис (у списку)", blank=True)
    instruction_text = models.TextField(
        "Інструкція/переваги та технічні відмінності", blank=True,
    )
    # поля для пошуку
    article = models.CharField("Артикул", max_length=128, blank=True, default="", db_index=True)
    code = models.CharField("Код", max_length=128, blank=True, default="", db_index=True)

    is_active = models.BooleanField("Активний", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Change товар"
        verbose_name_plural = "Change товари"
        ordering = ("title",)

    def __str__(self):
        return self.title


class AccessoryCategory(models.Model):
    name = models.CharField("Категорія аксесуарів", max_length=200, unique=True)
    instruction_text = models.TextField(
        "Текст для категорії аксесуарів", blank=True,
        help_text="Текст, який бот показує при натисканні на категорію",
    )

    class Meta:
        verbose_name = "Категорія аксесуарів"
        verbose_name_plural = "Категорії аксесуарів"
        ordering = ("name",)

    def __str__(self):
        return self.name


class Accessory(models.Model):
    category = models.ForeignKey(
        AccessoryCategory, on_delete=models.CASCADE, related_name="accessories", verbose_name="Категорія"
    )
    title = models.CharField("Назва аксесуара", max_length=255, db_index=True)
    short_note = models.TextField("Короткий опис (у списку)", blank=True)
    instruction_text = models.TextField(
        "Інструкція/аргументи для продажу", blank=True,
        help_text="Текст, який бот показує при натисканні на аксесуар",
    )
    is_active = models.BooleanField("Активний", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Аксесуар"
        verbose_name_plural = "Аксесуари"
        ordering = ("title",)

    def __str__(self):
        return self.title
