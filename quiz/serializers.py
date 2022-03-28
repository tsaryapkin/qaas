from typing import Any, Dict, List

from django.conf import settings
from django.core.exceptions import NON_FIELD_ERRORS
from django.db import transaction
from django.db.models import QuerySet
from django.db.utils import IntegrityError
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from taggit.serializers import TaggitSerializer, TagListSerializerField

from .models import *

__all__ = [
    "QuizMakerListSerializer",
    "QuizMakerSerializer",
    "InviteeListSerializer",
    "ParticipantSerializer",
    "QuestionSerializer",
    "AnswerSerializer",
    "InviteeSerializer",
    "TakeQuizSerializer",
    "ParticipantAnswerSerializer",
    "ParticipantProgressSerializer",
]


class RelatedManagerRepresentationMixin:
    def to_representation(self, data):
        return [
            self.child.to_representation(item) if item is not None else None
            for item in data.all()
        ]


class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = "id", "answer", "correct"


class AnswerListField(RelatedManagerRepresentationMixin, serializers.ListField):
    child = AnswerSerializer()


class QuestionSerializer(serializers.ModelSerializer):
    answers = AnswerListField(
        allow_empty=False,
        max_length=settings.MAX_ANSWERS_PER_QUESTION,
        min_length=2,
    )

    class Meta:
        model = Question
        fields = "id", "answers", "score", "question"

    def validate_answers(
        self, value: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        correct_ans_cnt = len([a for a in value if a["correct"]])
        if correct_ans_cnt == 0:
            raise ValidationError(
                {"answers": "Correct answer is not specified"}
            )
        if correct_ans_cnt > 1:
            raise ValidationError(
                {"answers": "More than one correct answer is specified"}
            )
        return value


class QuestionListField(
    RelatedManagerRepresentationMixin, serializers.ListField
):
    child = QuestionSerializer()


class QuizMakerSerializer(TaggitSerializer, serializers.ModelSerializer):
    questions = QuestionListField(
        allow_empty=False, max_length=settings.MAX_QUESTIONS_PER_QUIZ
    )
    tags = TagListSerializerField(required=False)

    class Meta:
        model = Quiz
        fields = "id", "title", "description", "questions", "tags"

    @classmethod
    def save_questions(
        cls, questions: List[Dict[str, Any]], quiz: Quiz
    ) -> None:
        for question in questions:
            q_answers = question.pop("answers")
            question["quiz"] = quiz
            saved = Question.objects.create(**question)
            cls.save_answers(q_answers, saved)

    @classmethod
    def save_answers(
        cls, answers: List[Dict[str, Any]], question: Question
    ) -> None:
        objs = [Answer(question=question, **answer) for answer in answers]
        Answer.objects.bulk_create(objs)

    def create(self, validated_data) -> Quiz:
        assert "questions" in validated_data, "No questions in request data"
        questions = validated_data.pop("questions")
        validated_data["author"] = self.context["request"].user
        with transaction.atomic():
            quiz = super().create(validated_data)
            self.save_questions(questions, quiz)
            return quiz


class QuizMakerListSerializer(TaggitSerializer, serializers.ModelSerializer):
    tags = TagListSerializerField()

    class Meta:
        model = Quiz
        exclude = ("author",)


class InviteeListSerializer(serializers.Serializer):
    invitees = serializers.ListField(
        child=serializers.EmailField(), max_length=100
    )


class ParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizParticipant
        fields = "id", "email", "status", "completed_at", "score_str"


class InviteeSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizInvitation
        exclude = "email", "created_at", "quiz"


class TakeAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = "id", "answer"


class TakeQuestionSerializer(serializers.ModelSerializer):
    answers = TakeAnswerSerializer(many=True)

    class Meta:
        model = Question
        fields = (
            "id",
            "question",
            "answers",
        )


class TakeQuizSerializer(TaggitSerializer, serializers.ModelSerializer):
    questions = TakeQuestionSerializer(many=True)
    tags = TagListSerializerField()

    class Meta:
        model = Quiz
        fields = "id", "slug", "title", "description", "questions", "tags"


class ParticipantRelatedQuestionField(serializers.PrimaryKeyRelatedField):
    """
    Extension to make sure that queryset returns only related to participant's quiz questions
    """

    def get_queryset(self) -> QuerySet[Question]:
        request = self.context.get("request", None)
        queryset = super().get_queryset()
        if not request or not queryset:
            return Question.objects.none()
        participant = request.participant
        if not participant:
            return Question.objects.none()
        return queryset.filter(quiz__id=participant.quiz.id).prefetch_related(
            "answers"
        )


class ParticipantAnswerSerializer(serializers.ModelSerializer):
    question = ParticipantRelatedQuestionField(queryset=Question.objects)
    answer = serializers.PrimaryKeyRelatedField(queryset=Answer.objects.all())

    class Meta:
        model = ParticipantAnswer
        fields = "question", "answer"

    def run_validation(self, *args, **kwargs):
        cleaned_data = super(ParticipantAnswerSerializer, self).run_validation(
            *args, **kwargs
        )
        if cleaned_data["answer"] not in cleaned_data["question"].answers.all():
            raise ValidationError({"answer": ["Wrong answer"]})
        return cleaned_data

    def create(self, validated_data):
        request = self.context.get("request")
        assert request is not None, "Request context is not provided"
        assert request.participant is not None, "Participant is not provided"
        validated_data["participant"] = request.participant
        try:
            return super(ParticipantAnswerSerializer, self).create(
                validated_data
            )
        except IntegrityError:  # attempt to answer question second time
            raise ValidationError(
                {NON_FIELD_ERRORS: ["You have already answered this question"]}
            )


class ParticipantProgressSerializer(serializers.ModelSerializer):
    answered_questions_count = serializers.IntegerField()
    total_questions_count = serializers.IntegerField()
    remaining_questions = TakeQuestionSerializer(many=True)

    class Meta:
        model = QuizParticipant
        fields = (
            "answered_questions_count",
            "total_questions_count",
            "remaining_questions",
        )
