from django.contrib import admin, messages
from django.contrib.admin import display
from invitations.admin import InvitationAdmin
from nested_admin.nested import (
    NestedModelAdmin,
    NestedStackedInline,
    NestedTabularInline,
)

from .forms import AnswerInlineFormset, QuestionInlineFormset, QuizAdminForm
from .models import *


class AnswerInline(NestedTabularInline):
    formset = AnswerInlineFormset
    model = Answer
    extra = 0
    min_num = 2


class QuestionInline(NestedStackedInline):
    formset = QuestionInlineFormset
    model = Question
    inlines = [AnswerInline]
    extra = 0
    min_num = 1


@admin.register(Quiz)
class QuizAdmin(NestedModelAdmin):
    list_display = ("author", "title", "slug", "created_at")
    list_filter = ("author",)
    search_fields = ("author__username", "title", "description")
    form = QuizAdminForm
    inlines = [QuestionInline]

    def has_add_permission(self, request, obj=None):
        return False

    @display(description="Author")
    def get_author(self, obj):
        return obj.author.username


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("quiz", "question", "score")
    list_filter = ("quiz",)
    search_fields = ("question",)
    inlines = [AnswerInline]

    def delete_model(self, request, obj):
        if obj.quiz.question_cnt == 1:
            storage = messages.get_messages(request)
            storage.used = True
            messages.error(request, "Cannot delete last record. Delete quiz instead")
        else:
            obj.delete()


@admin.register(QuizParticipant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ("email", "quiz", "status", "score", "progress")
    search_fields = ("quiz__name", "email")

    @display(description="Quiz")
    def get_quiz(self, obj):
        return obj.quiz.name


InvitationAdmin.list_display = ("email", "quiz", "sent", "accepted")
InvitationAdmin.list_filter = ("quiz",)
