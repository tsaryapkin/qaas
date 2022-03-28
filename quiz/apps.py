from django.apps import AppConfig


class QuizConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "quiz"

    def ready(self):
        from . import jobs  # noqa
        from . import signals  # noqa
