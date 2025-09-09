from __future__ import annotations

from django.contrib import admin
from django import forms

from .models import QAEntry, UnansweredQuestion, Category, QuestionLog, AllowedTelegramUser

# --------- QAEntry
@admin.register(QAEntry)
class QAEntryAdmin(admin.ModelAdmin):
    list_display = ('question', 'category')
    list_filter = ('category',)
    search_fields = ('question', 'answer')


# --------- Category
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ('name',)


# --------- QuestionLog
@admin.register(QuestionLog)
class QuestionLogAdmin(admin.ModelAdmin):
    list_display = ('question', 'answer_found', 'similarity', 'timestamp')
    list_filter = ('answer_found', 'timestamp')
    search_fields = ('question',)


# --------- UnansweredQuestion з додатковими полями
class UnansweredQuestionAdminForm(forms.ModelForm):
    synonyms = forms.CharField(
        label="Синоніми",
        required=False,
        help_text="Розділяй синоніми крапкою з комою ';'"
    )
    category = forms.ModelChoiceField(
        label="Категорія",
        queryset=Category.objects.all(),
        required=False
    )

    class Meta:
        model = UnansweredQuestion
        fields = ['question', 'proposed_answer', 'synonyms', 'category']


@admin.register(UnansweredQuestion)
class UnansweredQuestionAdmin(admin.ModelAdmin):
    form = UnansweredQuestionAdminForm
    list_display = ('question', 'asked_at', 'proposed_answer')
    search_fields = ('question',)

    def save_model(self, request, obj, form, change):
        if obj.question and obj.proposed_answer:
            # Створюємо QAEntry — embedding порахується всередині save()
            QAEntry.objects.create(
                question=obj.question,
                answer=obj.proposed_answer,
                synonyms=form.cleaned_data.get('synonyms'),
                category=form.cleaned_data.get('category'),
            )
            obj.delete()
        else:
            super().save_model(request, obj, form, change)


@admin.register(AllowedTelegramUser)
class AllowedTelegramUserAdmin(admin.ModelAdmin):
    list_display = ("user_id", "full_name", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("user_id", "full_name")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_per_page = 25
    actions = ("make_active", "make_inactive")

    @admin.action(description="Позначити як Активний")
    def make_active(self, request, queryset):
        updated = queryset.update(status=AllowedTelegramUser.Status.ACTIVE)
        self.message_user(request, f"Оновлено: {updated}")

    @admin.action(description="Позначити як Деактивований")
    def make_inactive(self, request, queryset):
        updated = queryset.update(status=AllowedTelegramUser.Status.INACTIVE)
        self.message_user(request, f"Оновлено: {updated}")
