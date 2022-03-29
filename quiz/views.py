import csv
import datetime
import json
from typing import Any, Dict, Optional

from annoying.functions import get_object_or_None
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import QuerySet
from django.http import HttpResponse
from invitations.exceptions import AlreadyAccepted, AlreadyInvited
from rest_framework import mixins, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from core.utils import datetime_to_str

from .filters import *
from .forms import CleanInvitationMixin
from .jobs import notify_participants
from .models import *
from .report import get_daily_report
from .serializers import *

__all__ = [
    "QuizMakerViewSet",
    "QuestionViewSet",
    "AnswerViewSet",
    "QuizViewSet",
    "accept_invitation",
    "daily_report",
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
        "progress": ProgressSerializer,
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
        status_code = status.HTTP_400_BAD_REQUEST
        if len(request.data) > settings.MAX_INVITEES_PER_REQUEST:
            raise APIException(
                code=status_code,
                detail=f"The number of invitees exceeds the limit: {settings.MAX_INVITEES_PER_REQUEST}",
            )
        response = {"valid": [], "invalid": []}
        for invitee in request.data:
            try:
                validate_email(invitee)
                CleanInvitationMixin().validate_invitation(invitee, quiz)
                invite = QuizInvitation.create(invitee, quiz=quiz, inviter=request.user)
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
            status_code = status.HTTP_201_CREATED

        return Response(data=response, status=status_code)

    @action(detail=True, methods=["get"])
    def invitees(self, request, *args, **kwargs) -> Response:
        quiz = self.get_object()
        self.filterset_class = InviteeFilter
        return self._paginated_response(quiz.invitations.all())

    @action(detail=True, methods=["post"])
    def notify(self, request, *args, **kwargs) -> Response:
        """Send notifications with results to those who completed the quiz"""
        quiz = self.get_object()
        notify_participants.delay(quiz.id)
        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def participants(self, request, *args, **kwargs) -> Response:
        """Quiz participants and their scores"""
        quiz = self.get_object()
        self.filterset_class = ParticipantFilter
        return self._paginated_response(quiz.participants.all())

    @action(detail=True, methods=["get"])
    def progress(self, request, *args, **kwargs) -> Response:
        quiz = self.get_object()
        return Response(self.get_serializer(quiz).data)

    @action(detail=True, methods=["get"])
    def questions(self, request, *args, **kwargs) -> Response:
        quiz = self.get_object()
        self.filterset_class = QuestionFilter
        return Response(QuestionSerializer(quiz.questions.all(), many=True).data)


class QuestionViewSet(
    ActionBasedSerializerMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    serializer_class = QuestionSerializer
    filterset_class = QuestionFilter

    serializer_action_classes = {
        "list": QuestionListSerializer,
    }

    def get_queryset(self) -> QuerySet[Quiz]:
        return Question.objects.filter(quiz__author=self.request.user).prefetch_related(
            "answers"
        )


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
    GenericViewSet,
):
    """
    Quizzes from participant's perspective - taking part, browsing, tracking progress etc
    """

    serializer_class = TakeQuizSerializer
    permission_classes = [AllowAny]
    queryset = Quiz.objects.all()
    filterset_class = QuizFilter
    token_header = "Quiz-token"

    serializer_action_classes = {
        "answer": ParticipantAnswerSerializer,
        "progress": ParticipantProgressSerializer,
        "list": QuizMakerListSerializer,
    }

    def get_queryset(self):
        return Quiz.for_user_or_participant(self.request.user, self.request.participant)

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
                detail="You have already completed this quiz",
                code=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            ParticipantProgressSerializer(participant).data,
            status=status.HTTP_200_OK,
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
    invitation: Optional[QuizInvitation] = get_object_or_None(QuizInvitation, key=key)
    if not invitation or invitation.key_expired():
        return Response(status=410, exception=True)
    if not invitation.accepted:
        invitation.accept(request)
    return Response(data={"quiz": f"{invitation.quiz.get_absolute_url()}?token={key}"})


@api_view(["GET"])
@permission_classes([IsAdminUser])
def daily_report(request: Request) -> HttpResponse:
    """
    Daily report about the usage of the service
    """
    known_formats = {"json": "application/json", "csv": "text/csv"}
    format_ = request.query_params.get("output_format", "csv")
    if format_ not in known_formats:
        return HttpResponse("Unknown format", status=status.HTTP_400_BAD_REQUEST)
    response_kwargs = {
        "content_type": known_formats[format_],
        "headers": {
            "Content-Disposition": f'attachment; filename="report-{datetime_to_str(datetime.datetime.now())}.{format_}"'
        },
    }
    report = get_daily_report()
    if format_ == "json":
        return HttpResponse(
            json.dumps(ReportSerializer(report).data), **response_kwargs
        )
    else:
        response = HttpResponse(**response_kwargs)
        writer = csv.writer(response)
        writer.writerows(report.as_rows)
        return response
