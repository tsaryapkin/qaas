import django_filters
from django.db.models import Q

from .models import *

__all__ = [
    "QuizFilter",
    "ParticipantFilter",
    "InviteeFilter",
    "QuestionFilter",
]


class QuizFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="_search", label="search")
    created = django_filters.DateFromToRangeFilter()

    def _search(self, queryset, name, value):
        return queryset.filter(
            Q(title__icontains=value)
            | Q(tags__name__icontains=value)
            | Q(description__icontains=value)  # case insensitive for postgresql
        ).distinct()


class BaseEmailFilter(django_filters.FilterSet):
    email = django_filters.CharFilter(
        lookup_expr="icontains"
    )  # case insensitive for postgresql


class ParticipantFilter(BaseEmailFilter):
    status = django_filters.ChoiceFilter(choices=QuizParticipant.STATUS)


class InviteeFilter(BaseEmailFilter):
    accepted = django_filters.BooleanFilter()


class QuestionFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(
        lookup_expr="icontains"
    )  # case insensitive for postgresql
    quiz = django_filters.ModelChoiceFilter(
        field_name="quiz", queryset=Quiz.objects.all()
    )


class AnswerFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(field_name="answer", lookup_expr="icontains")
    question = django_filters.ModelChoiceFilter(
        field_name="question", queryset=Question.objects.all()
    )
