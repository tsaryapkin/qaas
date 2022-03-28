from django import forms
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from invitations.adapters import get_invitations_adapter
from invitations.exceptions import AlreadyAccepted, AlreadyInvited

from .models import *


class CleanInvitationMixin(object):
    def validate_invitation(self, email, quiz) -> bool:
        if QuizInvitation.objects.all_valid().filter(
            email__iexact=email, quiz=quiz, accepted=False
        ):
            raise AlreadyInvited
        if QuizInvitation.objects.filter(
            email__iexact=email, quiz=quiz, accepted=True
        ):
            raise AlreadyAccepted
        else:
            return True

    def clean(self):
        cleaned_data = super().clean()
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
