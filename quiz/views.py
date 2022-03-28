from typing import Any, Dict, Optional

from annoying.functions import get_object_or_None
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import QuerySet
from invitations.exceptions import AlreadyAccepted, AlreadyInvited
from rest_framework import mixins, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from .filters import QuizFilter
from .forms import CleanInvitationMixin
from .models import *
from .serializers import *

__all__ = [
    "QuizMakerViewSet",
    "QuestionViewSet",
    "AnswerViewSet",
    "QuizViewSet",
    "accept_invitation",
]


class ActionBasedSerializerMixin:
    """Mixin-helper to get serializer class based on stored in a dict values"""

    serializer_action_classes: Dict[str, Any]

    def get_serializer_class(self):
        assert hasattr(self, "serializer_action_classes")
        return self.serializer_action_classes.get(
            self.action, super().get_serializer_class()
        )


class PaginatedQuerysetMixin:
    """
    Mixin-helper to paginate and filter queryset passed as an argument
    """

    def _paginated_response(self, queryset: QuerySet) -> Response:
        queryset = self.filter_queryset(queryset)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class QuizMakerViewSet(
    ActionBasedSerializerMixin,
    PaginatedQuerysetMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    """
    Quizzes from author's perspective. Creation, navigation, invites, progress, etc
    """

    permission_classes = [IsAuthenticated]
    serializer_class = QuizMakerSerializer
    serializer_action_classes = {
        "list": QuizMakerListSerializer,
        "invitees": InviteeSerializer,
        "participants": ParticipantSerializer,
    }
    filterset_class = QuizFilter

    def get_queryset(self) -> QuerySet[Quiz]:
        base_queryset = (
            Quiz.objects.all()
            if self.action in ["list", "invitees", "invite"]
            else Quiz.objects.deep()  # we will need info about questions and answers
        )
        return base_queryset.filter(author=self.request.user)

    @action(detail=True, methods=["post"])
    def invite(self, request, *args, **kwargs) -> Response:
        quiz = self.get_object()
        status_code = 400
        response = {"valid": [], "invalid": []}
        for invitee in request.data:
            try:
                validate_email(invitee)
                CleanInvitationMixin().validate_invitation(invitee, quiz)
                invite = QuizInvitation.create(
                    invitee, quiz=quiz, inviter=request.user
                )
            except ValidationError:
                response["invalid"].append({invitee: "invalid email"})
            except AlreadyAccepted:
                response["invalid"].append({invitee: "already accepted"})
            except AlreadyInvited:
                response["invalid"].append({invitee: "pending invite"})
            else:
                invite.send_invitation(request)
                response["valid"].append({invitee: "invited"})

        if response["valid"]:
            status_code = 201

        return Response(data=response, status=status_code)

    @action(detail=True, methods=["get"])
    def invitees(self, request, *args, **kwargs) -> Response:
        quiz = self.get_object()
        return self._paginated_response(quiz.invitations.all())

    @action(detail=True, methods=["get"])
    def participants(self, request, *args, **kwargs) -> Response:
        quiz = self.get_object()
        return self._paginated_response(quiz.participants.all())

    @action(detail=True, methods=["get"])
    def questions(self, request, *args, **kwargs) -> Response:
        quiz = self.get_object()
        return Response(
            QuestionSerializer(quiz.questions.all(), many=True).data
        )

    @action(detail=True, methods=["post"])
    def notify_participants(self, request, *args, **kwargs):
        quiz = self.get_object()
        quiz.notify_participants()
        return Response(status=200)


class QuestionViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    serializer_class = QuestionSerializer

    def get_queryset(self) -> QuerySet[Quiz]:
        return Question.objects.filter(
            quiz__author=self.request.user
        ).prefetch_related("answers")


class AnswerViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    serializer_class = AnswerSerializer

    def get_queryset(self) -> QuerySet[Quiz]:
        return Answer.objects.filter(question__quiz__author=self.request.user)


class QuizViewSet(
    ActionBasedSerializerMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    GenericViewSet,
):
    """
    Quizzes from participant's perspective
    """

    serializer_class = TakeQuizSerializer
    permission_classes = [AllowAny]
    queryset = Quiz.objects.all()
    lookup_field = "slug"
    token_header = "Quiz-token"

    serializer_action_classes = {
        "answer": ParticipantAnswerSerializer,
        "progress": ParticipantProgressSerializer,
    }

    def get_queryset(self):
        return Quiz.for_user_or_participant(
            self.request.user, self.request.participant
        )

    @classmethod
    def get_token(cls, request) -> Optional[str]:
        return request.GET.get("token") or request.headers.get(cls.token_header)

    def dispatch(self, request, *args, **kwargs):
        token = self.get_token(request)
        request.participant = (
            get_object_or_None(QuizParticipant, key=token) if token else None
        )
        response = super(QuizViewSet, self).dispatch(request, *args, **kwargs)
        if token:
            response.headers[self.token_header] = token
        return response

    @action(detail=True, methods=["post"])
    def answer(self, request, *args, **kwargs) -> Response:
        """Participant's answer to the question of the quiz"""
        participant = request.participant
        if not participant:
            participant = request.participant = get_object_or_None(
                QuizParticipant, user=request.user
            )
        if participant.status == QuizParticipant.STATUS.completed:
            raise APIException(
                detail="You have already completed this quiz", code=400
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            ParticipantProgressSerializer(participant).data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="my-progress",
    )
    def progress(self, request, *args, **kwargs) -> Response:
        """
        Participant's progress
        """
        serializer = self.get_serializer(request.participant)
        return Response(serializer.data)


@api_view(["GET"])
@permission_classes([AllowAny])
def accept_invitation(request, key) -> Response:
    """
    :param request
    :param key: token from invitation
    :return: Response - redirect to the quiz that the invite was about
    Creates participant
    """
    invitation: Optional[QuizInvitation] = get_object_or_None(
        QuizInvitation, key=key
    )
    if not invitation or invitation.key_expired():
        return Response(status=410, exception=True)
    if not invitation.accepted:
        invitation.accept(request)
    return Response(
        data={"quiz": f"{invitation.quiz.get_absolute_url()}?token={key}"}
    )
