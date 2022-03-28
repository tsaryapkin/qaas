from django.urls import re_path
from rest_framework.routers import DefaultRouter

from .views import *

router = DefaultRouter()

router.register("quizmaker/quizzes", QuizMakerViewSet, basename="quizmaker")
router.register("questions", QuestionViewSet, basename="questions")
router.register("answers", AnswerViewSet, basename="answers")
router.register("quizzes", QuizViewSet, basename="quizzes")


urlpatterns = router.urls
urlpatterns.append(
    re_path(
        r"accept-invite/(?P<key>\w+)/?$",
        accept_invitation,
        name="accept-invite",
    )
)
