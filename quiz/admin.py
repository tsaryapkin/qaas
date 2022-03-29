import logging

from django.contrib import admin, messages
from django.contrib.admin import display
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect
from invitations.admin import InvitationAdmin
from invitations.utils import (
    get_invitation_admin_add_form,
    get_invitation_admin_change_form,
    get_invitation_model,
)
from nested_admin.nested import (
    NestedModelAdmin,
    NestedStackedInline,
    NestedTabularInline,
)
from taggit.models import Tag

from .exceptions import QuizException
from .forms import AnswerInlineFormset, QuestionInlineFormset, QuizAdminForm
from .models import *

logger = logging.getLogger(__name__)


Invitation = get_invitation_model()
InvitationAdminAddForm = get_invitation_admin_add_form()
InvitationAdminChangeForm = get_invitation_admin_change_form()

admin.site.unregister(
    Invitation
)  # default invitation admin will be re-registered below
admin.site.unregister(Group)
admin.site.unregister(Tag)


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("email", "quiz", "sent", "accepted")
    list_filter = ("quiz",)

    def add_view(self, request, form_url="", extra_context=None):
        try:
            return super(InvitationAdmin, self).add_view(
                request, form_url, extra_context
            )
        except QuizException as e:
            logger.error("Failure to send invitation: smtp server is not available")
            self.message_user(request, str(e), level=logging.ERROR)
            return HttpResponseRedirect(request.path)

    def get_form(self, request, obj=None, **kwargs):
        if obj:
            kwargs["form"] = InvitationAdminChangeForm
        else:
            kwargs["form"] = InvitationAdminAddForm
            kwargs["form"].user = request.user
            kwargs["form"].request = request
        return super(InvitationAdmin, self).get_form(request, obj, **kwargs)


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
            messages.set_level(request, messages.ERROR)
            self.message_user(
                request,
                "You cannot delete the last question. Delete the quiz instead",
                level=logging.ERROR,
            )
            return HttpResponseRedirect(request.path)
        else:
            obj.delete()

    def get_readonly_fields(self, request, obj=None):
        return ["quiz"] if obj else []


@admin.register(QuizParticipant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ("email", "quiz", "status", "score", "progress")
    search_fields = ("quiz__name", "email")
    readonly_fields = ("key", "completed_at", "quiz")

    @display(description="Quiz")
    def get_quiz(self, obj):
        return obj.quiz.name
