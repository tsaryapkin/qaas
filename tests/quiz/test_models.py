import pytest
from faker import Faker

from quiz.models import *
from tests.factories import (
    QuizFactory,
    QuizInvitationFactory,
    QuizParticipantFactory,
    UserFactory,
)

fake = Faker()

pytestmark = pytest.mark.django_db


class FakeUser:
    is_authenticated = False


class FakeRequest:
    user = FakeUser()


def test_quiz_empty_queryset_without_user_and_participant():
    quiz = QuizFactory(questions=[])
    assert not quiz.for_user_or_participant(FakeUser(), None).exists()
    user = UserFactory()
    assert not Quiz.for_user_or_participant(user, None).exists()
    participant = QuizParticipantFactory()
    assert (
        not quiz.for_user_or_participant(FakeUser(), participant)
        .filter(id=quiz.id)
        .exists()
    )


def test_quiz_not_empty_queryset_with_user():
    user = UserFactory()
    QuizParticipantFactory(user=user)
    assert Quiz.for_user_or_participant(user, None).exists()


def test_quiz_not_empty_queryset_with_participant():
    participant = QuizParticipantFactory()
    assert Quiz.for_user_or_participant(FakeUser(), participant).exists()


def test_participant_status_changes(quiz):
    participant = QuizParticipantFactory(quiz=quiz)
    assert participant.status == QuizParticipant.STATUS.accepted
    questions = list(participant.quiz.questions.all())
    ParticipantAnswer.objects.create(
        participant=participant,
        question=questions[0],
        answer=questions[0].answers.first(),
    )
    participant.refresh_from_db()
    assert participant.status == QuizParticipant.STATUS.attempted
    ParticipantAnswer.objects.create(
        participant=participant,
        question=questions[1],
        answer=questions[1].answers.first(),
    )
    participant.refresh_from_db()
    assert participant.status == QuizParticipant.STATUS.completed


def test_participant_final_score_set(quiz):
    participant = QuizParticipantFactory(quiz=quiz)
    assert participant.status == QuizParticipant.STATUS.accepted
    questions = list(participant.quiz.questions.all())
    for question in questions:
        ParticipantAnswer.objects.create(
            participant=participant, question=question, answer=question.answers.first()
        )
    participant.refresh_from_db()
    assert participant.status == QuizParticipant.STATUS.completed
    assert participant.score >= 0


def test_user_associated_with_participant_if_exists():
    invitation = QuizInvitationFactory()
    user = UserFactory(email=invitation.email)
    invitation.accept(FakeRequest())
    participant = QuizParticipant.objects.get(email=invitation.email)
    assert participant is not None
    assert participant.user == user
