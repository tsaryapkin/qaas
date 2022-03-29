import datetime
from dataclasses import asdict, astuple, dataclass
from typing import Any, Dict, List

from django.db.models import Count, Q
from sql_util.utils import SubquerySum

from .models import *


@dataclass(slots=True)
class QuizReportEntry:
    title: str
    author: str
    questions_count: int
    created_at: datetime.datetime


@dataclass(slots=True)
class QuizParticipantEntry:
    quiz: str
    email: str
    status: str
    score: int
    answers_given: int
    created_at: datetime.datetime


@dataclass(slots=True)
class DailyReport:
    quizzes: List[QuizReportEntry]
    participants: List[QuizParticipantEntry]

    @property
    def as_dict(self) -> Dict:
        return asdict(self)

    @property
    def as_rows(self) -> List[List[Any]]:
        """Representation for csv"""
        result = [
            ["Quizzes"],
            ["Title", "Author", "Question count", "Created At"],
        ]
        result.extend([astuple(q) for q in self.quizzes])
        result.append([])
        result.append(["Participants"])
        result.append(["E-mail", "Quiz", "Status", "Score", "Answers given", "Created"])
        result.extend([astuple(p) for p in self.participants])
        return result


def _get_quiz_report_entries() -> List[QuizReportEntry]:
    quizzes = (
        Quiz.get_today_records()
        .annotate(
            question_count=Count("questions"),
        )
        .values("title", "author__username", "question_count", "created_at")
    )
    return [
        QuizReportEntry(
            title=record["title"],
            author=record["author__username"],
            questions_count=record["question_count"],
            created_at=record["created_at"],
        )
        for record in quizzes
    ]


def _get_participant_entries() -> List[QuizParticipantEntry]:
    participants = (
        QuizParticipant.get_today_records()
        .select_related("quiz")
        .annotate(
            answers_given=Count("answers"),
            score_=SubquerySum(
                "answers__answer__question__score",
                filter=Q(answers__correct=True),
            ),
        )
        .values(
            "email",
            "quiz__title",
            "answers_given",
            "created_at",
            "status",
            "score_",
        )
    )
    return [
        QuizParticipantEntry(
            email=record["email"],
            quiz=record["quiz__title"],
            score=record["score_"] or 0,
            answers_given=record["answers_given"],
            status=record["status"],
            created_at=record["created_at"],
        )
        for record in participants
    ]


def get_daily_report() -> DailyReport:
    return DailyReport(
        quizzes=_get_quiz_report_entries(),
        participants=_get_participant_entries(),
    )
