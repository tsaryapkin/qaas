from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils.text import slugify

from .models import *


@receiver(post_save, sender=ParticipantAnswer)
def on_participant_answer_saved(sender, instance: ParticipantAnswer, **kwargs) -> None:
    participant = instance.participant
    total_question_cnt = participant.quiz.question_cnt
    answered_so_far = participant.answered_questions_count
    if answered_so_far < total_question_cnt:
        participant.status = QuizParticipant.STATUS.attempted
    else:
        participant.status = QuizParticipant.STATUS.completed
        participant.score = participant._score
    participant.save()


@receiver(pre_save, sender=Quiz)
def on_quiz_pre_save(sender, instance: Quiz, **kwargs) -> None:
    if instance._state.adding:
        #  making sure that quiz has unique slug
        if not instance.slug:
            instance.slug = slugify(instance.title)
        if Quiz.objects.filter(slug=instance.slug).exists():
            instance.slug = f"{instance.slug}-{instance.id}"
