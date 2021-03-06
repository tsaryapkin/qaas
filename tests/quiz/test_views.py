import json
from datetime import datetime

import pytest
from faker import Faker
from rest_framework.reverse import reverse

from core.utils import generate_random_string
from tests.factories import *

fake = Faker()

pytestmark = pytest.mark.django_db


def test_fail_to_create_quiz_too_many_questions(client, user):
    client.force_login(user)
    response = client.post(
        reverse("quizmaker-list"),
        data=json.dumps(
            {
                "title": generate_random_string(),
                "questions": [
                    {
                        "question": generate_random_string(),
                        "answers": [
                            {"answer": "1", "correct": True},
                            {"answer": "2", "correct": False},
                        ],
                    }
                    for _ in range(5)
                ],
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "Ensure this field has no more than" in response.data["questions"][0]


def test_fail_to_create_quiz_too_many_answers(client, user):
    client.force_login(user)
    response = client.post(
        reverse("quizmaker-list"),
        data=json.dumps(
            {
                "title": generate_random_string(),
                "questions": [
                    {
                        "question": generate_random_string(),
                        "answers": [
                            {"answer": "1", "correct": True},
                            {"answer": "2", "correct": False},
                            {"answer": "2", "correct": False},
                            {"answer": "2", "correct": False},
                        ],
                    }
                ],
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert (
        "Ensure this field has no more than"
        in response.data["questions"][0]["answers"][0]
    )


def test_fail_to_create_quiz_multiple_right_answers(client, user):
    client.force_login(user)
    response = client.post(
        reverse("quizmaker-list"),
        data=json.dumps(
            {
                "title": generate_random_string(),
                "questions": [
                    {
                        "question": generate_random_string(),
                        "answers": [
                            {"answer": "1", "correct": True},
                            {"answer": "2", "correct": True},
                        ],
                    }
                ],
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert (
        "More than one correct answer"
        in response.data["questions"][0]["answers"]["answers"]
    )


def test_fail_to_create_quiz_no_right_answers(client, user):
    client.force_login(user)
    response = client.post(
        reverse("quizmaker-list"),
        data=json.dumps(
            {
                "title": generate_random_string(),
                "questions": [
                    {
                        "question": generate_random_string(),
                        "answers": [
                            {"answer": "1", "correct": False},
                            {"answer": "2", "correct": False},
                        ],
                    }
                ],
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert (
        "Correct answer is not specified"
        in response.data["questions"][0]["answers"]["answers"]
    )


def test_create_correct(client, user):
    client.force_login(user)
    response = client.post(
        reverse("quizmaker-list"),
        data=json.dumps(
            {
                "title": generate_random_string(),
                "questions": [
                    {
                        "question": generate_random_string(),
                        "answers": [
                            {"answer": "1", "correct": True},
                            {"answer": "2", "correct": False},
                        ],
                    }
                ],
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 201


def test_participant_cannot_answer_same_question_twice(client, quiz):
    participant = QuizParticipantFactory(quiz=quiz)
    question = quiz.questions.first()
    client.force_login(participant.user)
    request_data = {
        "question": question.id,
        "answer": question.answers.first().id,
    }
    url = reverse("quizzes-answer", args=[quiz.id])
    response = client.post(url, request_data)
    assert response.status_code == 200
    response = client.post(url, request_data)
    assert response.status_code == 400


def test_invitation_is_not_sent_twice(client, user):
    quiz = QuizFactory(questions=[], author=user)
    client.force_login(user)
    url = reverse("quizmaker-invite", args=[quiz.id])
    email = fake.email()
    response = client.post(
        url,
        data=json.dumps([email]),
        content_type="application/json",
    )
    assert response.status_code == 201
    assert email in response.data["valid"][0]
    assert response.data["valid"][0][email] == "invited"
    response = client.post(
        url,
        data=json.dumps([email]),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert email in response.data["invalid"][0]


def test_can_accept_invitation(client):
    quiz = QuizFactory(questions=[])
    invitation = QuizInvitationFactory(
        quiz=quiz, created_at=datetime.now(), sent=datetime.now()
    )
    url = reverse("accept-invite", args=[invitation.key])
    response = client.get(url)
    assert response.status_code == 200
    response = client.get(url)
    assert response.status_code == 200


def test_cannot_see_other_quizzes_author(client, user):
    QuizFactory(questions=[])
    client.force_login(user)
    url = reverse("quizmaker-list")
    response = client.get(url)
    assert response.status_code == 200
    assert response.data["count"] == 0


def test_can_see_own_quizzes_author(client, user):
    quiz = QuizFactory(questions=[], author=user)
    client.force_login(user)
    url = reverse("quizmaker-list")
    response = client.get(url)
    assert response.status_code == 200
    assert response.data["count"] == 1
    url = reverse("quizmaker-detail", args=[quiz.id])
    response = client.get(url)
    assert response.status_code == 200
    assert response.data["id"] == quiz.id


def test_can_my_quiz_as_participant(client, user):
    participant = QuizParticipantFactory(user=user)
    quiz = participant.quiz
    client.force_login(user)
    url = reverse("quizzes-list")
    response = client.get(url)
    assert response.status_code == 200
    assert response.data["count"] == 1
    url = reverse("quizzes-detail", args=[quiz.id])
    response = client.get(url)
    assert response.status_code == 200
    assert response.data["id"] == quiz.id


def test_cannot_see_quizzes_that_i_am_not_invited(client, user):
    QuizFactory(questions=[])
    client.force_login(user)
    url = reverse("quizzes-list")
    response = client.get(url)
    assert response.status_code == 200
    assert response.data["count"] == 0
