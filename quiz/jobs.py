from typing import Any, Dict, List, Optional

from annoying.functions import get_object_or_None
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core import mail
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string

from qaas.celery import app
from quiz.models import Quiz, QuizParticipant

logger = get_task_logger(__name__)


def _render_notification(
    email: str,
    context: Dict[str, Any],
    template_prefix: str = "quiz/notifications/notification",
) -> EmailMessage:
    subject = render_to_string(f"{template_prefix}_subject.txt", context)
    subject = " ".join(subject.splitlines()).strip()

    bodies = {}
    for ext in ["html", "txt"]:
        try:
            template_name = f"{template_prefix}_body.{ext}"
            bodies[ext] = render_to_string(template_name, context).strip()
        except TemplateDoesNotExist:
            if ext == "txt" and not bodies:
                raise
    if "txt" in bodies:
        msg = EmailMultiAlternatives(
            subject, bodies["txt"], settings.DEFAULT_FROM_EMAIL, [email]
        )
        if "html" in bodies:
            msg.attach_alternative(bodies["html"], "text/html")
    else:
        msg = EmailMessage(
            subject, bodies["html"], settings.DEFAULT_FROM_EMAIL, [email]
        )
        msg.content_subtype = "html"
    return msg


@app.task(name="notify_participants")
def notify(quiz_id: int) -> List[int]:
    quiz = get_object_or_None(Quiz, id=quiz_id)
    quiz_summary = list(quiz.summary(notified=False))
    messages = [
        _render_notification(participant["email"], participant)
        for participant in quiz_summary
    ]
    if messages:
        try:
            with mail.get_connection():
                for msg in messages:
                    msg.send()
            return [p["id"] for p in quiz_summary]
        except ConnectionError as e:
            logger.info(f"Mail connection error, details: {e}")


@app.task(name="set_notified")
def set_notified(participant_ids: Optional[List[int]]) -> None:
    if participant_ids:
        QuizParticipant.objects.filter(id__in=participant_ids).update(notified=True)


def notify_participants(quiz: Quiz) -> None:
    (notify.s(quiz.id) | set_notified.s()).apply_async()
