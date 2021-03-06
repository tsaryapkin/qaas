from django import forms
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.forms import inlineformset_factory
from invitations.adapters import get_invitations_adapter
from invitations.exceptions import AlreadyAccepted, AlreadyInvited

from .models import *


class CleanInvitationMixin(object):
    def validate_invitation(self, email, quiz) -> bool:
        if QuizInvitation.objects.all_valid().filter(
            email__iexact=email, quiz=quiz, accepted=False
        ):
            raise AlreadyInvited
        if QuizInvitation.objects.filter(email__iexact=email, quiz=quiz, accepted=True):
            raise AlreadyAccepted
        else:
            return True

    def clean(self):
        cleaned_data = super().clean()  # type: ignore
        email = cleaned_data["email"]
        email = get_invitations_adapter().clean_email(email)
        errors = {
            "already_accepted": "This e-mail address has already accepted an invite.",
        }
        quiz = cleaned_data["quiz"]
        try:
            self.validate_invitation(email, quiz)
        except AlreadyAccepted:
            raise forms.ValidationError(errors["already_accepted"])
        return cleaned_data


class QuizInvitationAdminAddForm(CleanInvitationMixin, forms.ModelForm):
    email = forms.EmailField(
        label="E-mail",
        required=True,
        widget=forms.TextInput(attrs={"type": "email", "size": "30"}),
    )

    def save(self, *args, **kwargs):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        quiz = cleaned_data.get("quiz")
        params = {"email": email, "quiz": quiz}
        if cleaned_data.get("inviter"):
            params["inviter"] = cleaned_data.get("inviter")
        instance = QuizInvitation.create(**params)
        instance.send_invitation(self.request)
        super().save(*args, **kwargs)
        return instance

    class Meta:
        model = QuizInvitation
        fields = ("email", "inviter", "quiz")


class QuizAdminForm(forms.ModelForm):
    class Meta:
        model = Quiz
        exclude = "created", "modified", "published_at"


class QuestionInlineFormset(forms.BaseInlineFormSet):
    model = Question

    def add_fields(self, form, index):
        super().add_fields(form, index)
        question_field = forms.CharField(widget=forms.TextInput())
        question_field.widget.attrs["size"] = 150
        form.fields["question"] = question_field

    def clean(self):
        super().clean()
        if not [form for form in self.forms if not form.cleaned_data.get("DELETE")]:
            raise ValidationError(
                [{NON_FIELD_ERRORS: "Min 1 question should be specified"}]
            )


class AnswerInlineFormset(forms.BaseInlineFormSet):
    model = Answer

    def clean(self):
        super().clean()
        correct_cnt = 0
        to_delete = 0
        for form in self.forms:
            if form.cleaned_data.get("correct"):
                correct_cnt += 1
            if form.cleaned_data.get("DELETE"):
                to_delete += 1
        if correct_cnt == 0:
            raise ValidationError(
                [{NON_FIELD_ERRORS: "Correct answer is not specified"}]
            )
        if correct_cnt > 1:
            raise ValidationError(
                [{NON_FIELD_ERRORS: "More than one correct answer is specified"}]
            )
        if len(self.forms) - to_delete < 2 and not self.parent_form.cleaned_data.get(
            "DELETE"
        ):
            #  if question is not deleted there needs to be at least two answers
            raise ValidationError(
                [{NON_FIELD_ERRORS: "Min 2 answers should be specified"}]
            )


QuestionAnswerFormset = inlineformset_factory(
    Question, Answer, fields=("answer", "correct"), extra=1
)
