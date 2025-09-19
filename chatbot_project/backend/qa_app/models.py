from __future__ import annotations

from django.db import models, transaction
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
    # Залишаємо старе поле embedding для зворотної сумісності (можете прибрати пізніше)
    embedding = VectorField(
        blank=True, null=True,
        dimensions=getattr(settings, "EMBED_DIMENSIONS", 1536)
    )

    class Meta:
        verbose_name = "Питання і відповідь"
        verbose_name_plural = "Питання і відповіді"

    def __str__(self):
        return self.question

    # ---- variants helpers
    def get_variants_list(self) -> list[str]:
        out = [self.question.strip()]
        if self.synonyms:
            out += [s.strip() for s in self.synonyms.split(";") if s.strip()]
        # унікалізація, зберігаємо порядок
        seen = set()
        uniq = []
        for t in out:
            if t not in seen:
                uniq.append(t)
                seen.add(t)
        return uniq

    @transaction.atomic
    def save(self, *args, **kwargs):
        """
        1) Зберігаємо сам QAEntry.
        2) Перегенеровуємо варіанти (питання + синоніми) у таблиці QAVariant з ОКРЕМИМИ embedding.
        3) Поле embedding у QAEntry оновлюємо embedding-ом головного питання (можна прибрати згодом).
        """
        super().save(*args, **kwargs)

        # 3. QAEntry.embedding = embedding головного питання (для сумісності)
        q = (self.question or "").strip()
        self.embedding = embed_text_sync(q) if q else None
        super().save(update_fields=["embedding"])

        # 2. повністю перебудовуємо QAVariant
        QAVariant.objects.filter(entry=self).delete()
        for text in self.get_variants_list():
            vec = embed_text_sync(text)
            QAVariant.objects.create(entry=self, text=text, embedding=vec)


class QAVariant(models.Model):
    entry = models.ForeignKey(
        QAEntry,
        on_delete=models.CASCADE,
        related_name="variants",
        db_index=True,
    )
    text = models.TextField("Варіант", db_index=True)
    embedding = VectorField(
        blank=True, null=True,
        dimensions=getattr(settings, "EMBED_DIMENSIONS", 1536)
    )

    class Meta:
        verbose_name = "Варіант формулювання"
        verbose_name_plural = "Варіанти формулювань"

    def __str__(self):
        return f"[{self.entry_id}] {self.text}"


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

    # ⬇️ НОВЕ: хто задав (зв'язок із AllowedTelegramUser)
    asked_by = models.ForeignKey(
        AllowedTelegramUser,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Хто задав",
        related_name="question_logs",
        db_index=True,
    )

    class Meta:
        verbose_name = "Запит користувача"
        verbose_name_plural = "Запити користувачів"

    def __str__(self):
        return self.question
