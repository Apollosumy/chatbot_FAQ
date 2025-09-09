from django.db import models

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class InstructionCategory(models.Model):
    name = models.CharField("Назва категорії", max_length=100, unique=True)

    class Meta:
        verbose_name = "Категорія інструкцій"
        verbose_name_plural = "Категорії інструкцій"

    def __str__(self):
        return self.name


class InstructionSubcategory(models.Model):
    category = models.ForeignKey(InstructionCategory, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField("Назва підкатегорії", max_length=100)

    class Meta:
        unique_together = ('category', 'name')
        verbose_name = "Підкатегорія"
        verbose_name_plural = "Підкатегорії"

    def __str__(self):
        return f"{self.category.name} — {self.name}"


class Instruction(models.Model):
    subcategory = models.ForeignKey(InstructionSubcategory, on_delete=models.CASCADE, related_name='instructions')
    title = models.CharField("Назва інструкції", max_length=200)
    content = models.TextField("Текст інструкції")
    image = models.ImageField("Зображення", upload_to='instructions/', blank=True, null=True)
    tags = models.ManyToManyField('Tag', related_name='instructions', blank=True)  # Додати цей рядок

    class Meta:
        verbose_name = "Інструкція"
        verbose_name_plural = "Інструкції"

    def __str__(self):
        return self.title
