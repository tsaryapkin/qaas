from typing import Any, Dict

from annoying.functions import get_object_or_None
from django.conf import settings
from django.core import mail
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string

from qaas.celery import app
from quiz.models import Quiz


def render_notification(
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


@app.task
def notify_participants(quiz_id: int) -> None:
    quiz = get_object_or_None(Quiz, id=quiz_id)
    quiz_summary = quiz.summary()
    messages = [
        render_notification(participant["email"], participant)
        for participant in quiz_summary
    ]
    with mail.get_connection():
        for msg in messages:
            msg.send()
