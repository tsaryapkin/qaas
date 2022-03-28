import django_filters


class QuizFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(lookup_expr="icontains")
    tags = django_filters.CharFilter(field_name="tags__name")
    created = django_filters.DateFromToRangeFilter()


class ParticipantFilter(django_filters.FilterSet):
    email = django_filters.CharFilter(lookup_expr="icontains")
