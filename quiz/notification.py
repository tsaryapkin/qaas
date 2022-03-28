from abc import ABC, abstractmethod
from typing import Any, Dict

from django.conf import settings
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string

from .models import Quiz, QuizParticipant

__all__ = []


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


def notify_participants(quiz: Quiz):
    context = {"quiz_title": quiz.title, "max_score": quiz.max_score}
    participants = quiz.participants.filter(
        status=QuizParticipant.STATUS.completed
    ).values("score")
