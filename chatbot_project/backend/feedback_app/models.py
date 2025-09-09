from django.db import models

class BotFeedback(models.Model):
    user_id = models.CharField("ID користувача", max_length=50, blank=True, null=True)
    message = models.TextField("Повідомлення")
    submitted_at = models.DateTimeField("Дата подання", auto_now_add=True)
    is_resolved = models.BooleanField("Оброблено", default=False)

    class Meta:
        verbose_name = "Відгук про бота"
        verbose_name_plural = "Відгуки про бота"

    def __str__(self):
        return f"{self.submitted_at:%Y-%m-%d %H:%M} — {'✅' if self.is_resolved else '❌'}"
