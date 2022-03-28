import pytest

from .factories import AnswerFactory, QuestionFactory, QuizFactory, UserFactory


@pytest.fixture(autouse=True)
def use_dummy_max_cnt(settings):
    settings.MAX_QUESTIONS_PER_QUIZ = 3
    settings.MAX_ANSWERS_PER_QUESTION = 2
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


@pytest.fixture
def user():
    return UserFactory(username="test", password="test")


def question(quiz):
    question = QuestionFactory(quiz=quiz)
    question.answers.add(AnswerFactory(question=question, correct=True))
    question.answers.add(AnswerFactory(question=question, correct=False))
    return question


@pytest.fixture
def quiz():
    quiz = QuizFactory(questions=[])
    quiz.questions.add(question(quiz))
    quiz.questions.add(question(quiz))
    return quiz
