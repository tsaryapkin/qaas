from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from quiz.models import QuizParticipant

UserModel = get_user_model()


@receiver(post_save, sender=UserModel, dispatch_uid="user_post_save")
def on_user_post_save(
    sender, instance: UserModel, created: bool, **kwargs
) -> None:
    if created and instance.email:
        # We need to associate all participant records without user but with new user's email to newly created user
        QuizParticipant.objects.filter(
            email=instance, user__isnull=True
        ).update(user=instance)
