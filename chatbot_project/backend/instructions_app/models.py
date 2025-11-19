from django.db import models


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"

    def __str__(self) -> str:
        return self.name


class InstructionNode(models.Model):
    """
    Вузол дерева інструкцій:
    - root (parent=None)  -> "категорія"
    - child               -> "підкатегорія" / "підпідкатегорія" і т.д.
    Глибина не обмежена.
    """
    name = models.CharField("Назва розділу", max_length=100)

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="children",
        null=True,
        blank=True,
        verbose_name="Батьківський розділ",
    )

    class Meta:
        verbose_name = "Розділ інструкцій"
        verbose_name_plural = "Розділи інструкцій"
        constraints = [
            models.UniqueConstraint(
                fields=["parent", "name"],
                name="unique_instructionnode_per_parent",
            )
        ]

    def __str__(self) -> str:
        return self.full_path

    @property
    def is_root(self) -> bool:
        return self.parent is None

    @property
    def full_path(self) -> str:
        """
        Людяний шлях типу:
        "Категорія / Підкатегорія / Підпідкатегорія"
        """
        parts = [self.name]
        parent = self.parent
        while parent is not None:
            parts.append(parent.name)
            parent = parent.parent
        return " / ".join(reversed(parts))


class Instruction(models.Model):
    node = models.ForeignKey(
        InstructionNode,
        on_delete=models.CASCADE,
        related_name="instructions",
        verbose_name="Розділ",
        help_text="Розділ дерева, до якого належить інструкція.",
        null=True,   # важливо для існуючих записів
        blank=True,  # щоб адмінка не падала, поки не привʼяжеш
    )
    title = models.CharField("Назва інструкції", max_length=200)
    content = models.TextField("Текст інструкції")
    image = models.ImageField(
        "Зображення",
        upload_to="instructions/",
        blank=True,
        null=True,
    )
    tags = models.ManyToManyField(
        Tag,
        related_name="instructions",
        blank=True,
        verbose_name="Теги",
    )

    class Meta:
        verbose_name = "Інструкція"
        verbose_name_plural = "Інструкції"

    def __str__(self) -> str:
        return self.title
