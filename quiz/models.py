import datetime
import logging
from functools import reduce
from itertools import groupby
from operator import itemgetter, or_
from typing import Any, Dict, Iterable, Iterator, Optional, Tuple

from django.db import IntegrityError, models, transaction
from django.db.models import Prefetch, Q, QuerySet, Subquery, Sum
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from invitations.adapters import get_invitations_adapter
from invitations.app_settings import app_settings
from invitations.base_invitation import AbstractBaseInvitation
from model_utils import Choices
from model_utils.fields import MonitorField, StatusField
from ordered_model.models import OrderedModel
from rest_framework.reverse import reverse
from taggit.managers import TaggableManager

from core.models import TimestampedModel
from core.utils import compact, percentage
from users.models import User

from .exceptions import QuizException

logger = logging.getLogger(__name__)

__all__ = [
    "Quiz",
    "Question",
    "QuizParticipant",
    "Answer",
    "QuizInvitation",
    "ParticipantAnswer",
]


class DeepQuizQueryset(models.QuerySet):
    def deep(self):
        return self.prefetch_related(
            Prefetch(
                "questions",
                queryset=Question.objects.prefetch_related("answers"),
            )
        )


class Quiz(TimestampedModel):
    STATUS = Choices("draft", "published", "closed")

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="quizzes",
        verbose_name="author",
    )
    title = models.CharField(
        max_length=255,
        null=False,
        blank=False,
        verbose_name="title",
        unique=True,
    )
    description = models.TextField(
        max_length=1000, null=True, blank=True, verbose_name="description"
    )
    slug = models.SlugField(
        null=False, blank=True, unique=True, verbose_name="slug"
    )
    tags = TaggableManager()

    objects = DeepQuizQueryset.as_manager()

    class Meta:
        verbose_name = _("Quiz")
        verbose_name_plural = _("Quizzes")

    def __str__(self) -> str:
        return self.title

    @property
    def question_cnt(self) -> int:
        return self.questions.count()

    @classmethod
    def for_user_or_participant(
        cls, user: User, participant: Optional["QuizParticipant"] = None
    ) -> QuerySet["Quiz"]:
        """Returns queryset of quizzes related to user-participant or quizParticipant when user is anonymous"""
        if not (user.is_authenticated or participant):
            # if user is not authenticated and participant is not provided via token, there's nothing to return
            return Quiz.objects.none()
        criteria = [
            Q(participants__user=user) if user.is_authenticated else None,
            Q(participants__id=participant.id) if participant else None,
        ]
        return (
            cls.objects.prefetch_related("participants")
            .filter(reduce(or_, compact(criteria)))
            .distinct()
        )

    def get_absolute_url(self):
        return reverse("quizzes-detail", args=[self.id])

    @property
    def max_score(self) -> int:
        """Max number of scores that can be achieved"""
        return self.questions.all().aggregate(Sum("score"))["score__sum"]

    def summary(self) -> Iterable[Dict[str, Any]]:
        common_context = {"quiz_title": self.title, "max_score": self.max_score}
        participants = (
            self.participants.prefetch_related(
                Prefetch(
                    "answers",
                    queryset=ParticipantAnswer.objects.select_related("answer"),
                )
            )
            .filter(status=QuizParticipant.STATUS.completed)
            .order_by("id", "answers__answer__id")
            .values(
                "email",
                "score",
                "answers__answer__correct",
                "answers__answer__answer",
                "answers__answer__id",
                "answers__answer__question__question",
            )
        )

        def map_to_context(
            participant_data: Tuple[str, Iterator]
        ) -> Dict[str, Any]:
            assert participant_data
            email, answers = participant_data
            answers = list(answers)
            context_ = {
                "email": email,
                "answers": [
                    {
                        "question": answer[
                            "answers__answer__question__question"
                        ],
                        "answer": answer["answers__answer__answer"],
                        "correct": answer["answers__answer__correct"],
                    }
                    for answer in answers
                ],
                "score": answers[0]["score"],
            }
            context_.update(common_context)
            return context_

        return map(
            map_to_context, groupby(participants, key=itemgetter("email"))
        )


class QuizInvitation(AbstractBaseInvitation):
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="invitations",
        verbose_name="quiz",
    )
    email = models.EmailField(verbose_name="e-mail address")
    created = models.DateTimeField(verbose_name="created", default=timezone.now)

    class Meta:
        unique_together = "quiz", "email"

    @classmethod
    def create(cls, email, inviter=None, **kwargs) -> "QuizInvitation":
        assert "quiz" in kwargs
        quiz = kwargs["quiz"]
        key = get_random_string(64).lower()
        return QuizInvitation.objects.create(
            email=email, key=key, inviter=inviter, quiz=quiz
        )

    def key_expired(self):
        expiration_date = self.sent + datetime.timedelta(
            days=app_settings.INVITATION_EXPIRY
        )
        return expiration_date <= timezone.now()

    def send_invitation(self, request, **kwargs):
        invite_url = reverse("accept-invite", args=[self.key])
        invite_url = request.build_absolute_uri(invite_url)
        ctx = kwargs
        ctx.update(
            {
                "invite_url": invite_url,
                "site_name": f"quiz {self.quiz.title.capitalize()}",
                "email": self.email,
                "key": self.key,
                "inviter": self.inviter,
            }
        )

        email_template = "invitations/email/email_invite"
        try:
            get_invitations_adapter().send_mail(email_template, self.email, ctx)
        except ConnectionError as e:
            logger.error(f"SMTP server is not available, details: {e}")
            raise QuizException("Mail service is temporarily unavailable")
        self.sent = timezone.now()
        self.save()

    def __str__(self):
        return f"Quiz invite: {self.email}"

    def accept(self, request) -> None:
        """Creates participant record from invitation"""
        user = request.user if request.user.is_authenticated else None
        with transaction.atomic():
            self.accepted = True
            self.save()
            try:
                QuizParticipant.objects.create(
                    user=user, key=self.key, email=self.email, quiz=self.quiz
                )
            except IntegrityError:  # attempt to create participant with existing combination of email and quiz
                raise QuizException(
                    detail="Participant with this email is already taking part in this quiz"
                )


class QuizParticipant(TimestampedModel):
    STATUS = Choices("accepted", "attempted", "completed")

    email = models.EmailField(verbose_name="e-mail")
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="participants",
        verbose_name="quizzes",
        null=True,
    )
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="participants",
        verbose_name="participants",
    )
    status = StatusField(default=STATUS.accepted, verbose_name="status")
    score = models.PositiveIntegerField(null=True)

    key = models.CharField(max_length=100, null=False)
    completed_at = MonitorField(monitor="status", when=["completed"], null=True)

    class Meta:
        verbose_name = _("Participant")
        verbose_name_plural = _("Participants")
        unique_together = ("email", "quiz")

    @property
    def answered_questions_count(self) -> int:
        return self.answers.count()

    @property
    def total_questions_count(self) -> int:
        return self.quiz.question_cnt

    @property
    def progress(self) -> str:
        if self.status == self.STATUS.completed:
            return "100%"
        return percentage(
            self.answered_questions_count, self.total_questions_count
        )

    @property
    def remaining_questions(self) -> QuerySet["Question"]:
        """Questions that haven't been answered by participant"""
        if self.status == self.STATUS.completed:
            return Question.objects.none()
        return self.quiz.questions.exclude(
            id__in=Subquery(self.answers.values("question__id"))
        ).prefetch_related("answers")

    @property
    def _score(self) -> int:
        return (
            self.answers.prefetch_related("answer", "answer__question")
            .filter(answer__correct=True)
            .aggregate(Sum("answer__question__score"))[
                "answer__question__score__sum"
            ]
        )

    @property
    def score_str(self) -> str:
        return f"{self.score or self._score} out of {self.quiz.max_score}"

    def __str__(self) -> str:
        return f"Participant {self.email} - quiz {self.quiz.title}"


class Question(OrderedModel):
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="questions",
        verbose_name="quiz",
    )
    question = models.TextField(max_length=300, verbose_name="question")
    score = models.PositiveIntegerField(default=1, verbose_name="score")

    order_with_respect_to = "quiz"

    class Meta:
        verbose_name = _("Question")
        verbose_name_plural = _("Questions")
        ordering = ("quiz", "order")

    def __str__(self) -> str:
        return self.question


class Answer(OrderedModel):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="answers",
        verbose_name="question",
    )
    answer = models.CharField(max_length=1024, verbose_name="answer")
    correct = models.BooleanField(null=False, default=False)

    order_with_respect_to = "question"

    class Meta:
        verbose_name = _("Answer")
        verbose_name_plural = _("Answers")
        ordering = (
            "question",
            "order",
        )

    def __str__(self) -> str:
        return self.answer


class ParticipantAnswer(TimestampedModel):
    participant = models.ForeignKey(
        QuizParticipant, on_delete=models.CASCADE, related_name="answers"
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("Participant's answer")
        verbose_name_plural = _("Participant's answers")
        unique_together = "participant", "question", "answer"
