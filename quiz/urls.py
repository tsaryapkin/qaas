from django.urls import path, re_path
from rest_framework.routers import DefaultRouter

from .views import *

router = DefaultRouter()

router.register("quizmaker/quizzes", QuizMakerViewSet, basename="quizmaker")
router.register("questions", QuestionViewSet, basename="questions")
router.register("answers", AnswerViewSet, basename="answers")
router.register("quizzes", QuizViewSet, basename="quizzes")


urlpatterns = router.urls
urlpatterns += [
    re_path(
        r"accept-invite/(?P<key>\w+)/?$",
        accept_invitation,
        name="accept-invite",
    ),
    path("report/", daily_report, name="daily-report"),
]
