import json
from datetime import datetime

import pytest
from faker import Faker
from rest_framework.reverse import reverse

from tests.factories import *

fake = Faker()

pytestmark = pytest.mark.django_db


def test_fail_to_create_quiz_too_many_questions(client, user):
    client.force_login(user)
    response = client.post(
        "/api/quizmaker/quizzes/",
        data=json.dumps(
            {
                "title": fake.sentence(),
                "questions": [
                    {
                        "question": fake.sentence(),
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
        "/api/quizmaker/quizzes/",
        data=json.dumps(
            {
                "title": fake.sentence(),
                "questions": [
                    {
                        "question": fake.sentence(),
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
        "/api/quizmaker/quizzes/",
        data=json.dumps(
            {
                "title": fake.sentence(),
                "questions": [
                    {
                        "question": fake.sentence(),
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
        "/api/quizmaker/quizzes/",
        data=json.dumps(
            {
                "title": fake.sentence(),
                "questions": [
                    {
                        "question": fake.sentence(),
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
        "/api/quizmaker/quizzes/",
        data=json.dumps(
            {
                "title": fake.sentence(),
                "questions": [
                    {
                        "question": fake.sentence(),
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
    url = f"/api/quizzes/{quiz.slug}/answer/"
    response = client.post(url, request_data)
    assert response.status_code == 201
    response = client.post(url, request_data)
    assert response.status_code == 400


def test_invitation_is_not_sent_twice(client, user):
    quiz = QuizFactory(questions=[], author=user)
    client.force_login(user)
    url = f"/api/quizmaker/quizzes/{quiz.id}/invite/"
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
        quiz=quiz, created=datetime.now(), sent=datetime.now()
    )
    url = reverse("accept-invite", args=[invitation.key])
    response = client.get(url)
    assert response.status_code == 200
    response = client.get(url)
    assert response.status_code == 200
