from __future__ import annotations

from django.db import models
from django.conf import settings
from pgvector.django import VectorField
from qa_app.services.embeddings import embed_text_sync


class Category(models.Model):
    name = models.CharField("Категорія", max_length=100, unique=True)

    class Meta:
        verbose_name = "Категорія"
        verbose_name_plural = "Категорії"

    def __str__(self):
        return self.name


class QAEntry(models.Model):
    question = models.TextField("Питання", unique=True)
    synonyms = models.TextField(
        "Синоніми", blank=True, null=True,
        help_text="Список синонімів, розділених крапкою з комою ';'"
    )
    answer = models.TextField("Відповідь")
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Категорія"
    )
    embedding = VectorField(
        blank=True, null=True,
        dimensions=getattr(settings, "EMBED_DIMENSIONS", 1536)
    )

    class Meta:
        verbose_name = "Питання і відповідь"
        verbose_name_plural = "Питання і відповіді"

    def __str__(self):
        return self.question

    def get_all_variants(self):
        variants = [self.question]
        if self.synonyms:
            variants.extend([syn.strip() for syn in self.synonyms.split(";") if syn.strip()])
        return variants

    def save(self, *args, **kwargs):
        """
        Вираховуємо embedding у sync-режимі (save() — синхронний API Django).
        Якщо текстів немає — embedding не чіпаємо.
        """
        all_variants = self.get_all_variants()
        if all_variants:
            text = " ".join(all_variants)
            self.embedding = embed_text_sync(text)
        super().save(*args, **kwargs)


class UnansweredQuestion(models.Model):
    question = models.TextField("Питання без відповіді", unique=True)
    proposed_answer = models.TextField("Відповідь", blank=True, null=True)
    asked_at = models.DateTimeField("Дата запиту", auto_now_add=True)

    class Meta:
        verbose_name = "Питання без відповіді"
        verbose_name_plural = "Питання без відповідей"

    def __str__(self):
        return self.question


class AllowedTelegramUser(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Активний"
        INACTIVE = "inactive", "Деактивований"

    full_name = models.CharField("ПІБ", max_length=255, blank=True, default="")
    user_id = models.BigIntegerField("Telegram ID", unique=True, db_index=True)
    status = models.CharField(
        "Статус",
        max_length=16,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    created_at = models.DateTimeField("Додано", auto_now_add=True)

    class Meta:
        verbose_name = "Дозволений користувач Telegram"
        verbose_name_plural = "Дозволені користувачі Telegram"
        ordering = ("-created_at",)

    def __str__(self):
        label = self.full_name or str(self.user_id)
        return f"{label} — {self.get_status_display()}"


class QuestionLog(models.Model):
    question = models.TextField("Запит користувача")
    answer_found = models.BooleanField("Відповідь знайдена")
    similarity = models.FloatField("Схожість", blank=True, null=True)
    timestamp = models.DateTimeField("Час запиту", auto_now_add=True)

    class Meta:
        verbose_name = "Запит користувача"
        verbose_name_plural = "Запити користувачів"

    def __str__(self):
        return self.question
