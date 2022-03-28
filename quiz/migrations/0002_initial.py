# Generated by Django 3.2.12 on 2022-03-28 04:59

import django.db.models.deletion
import taggit.managers
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("quiz", "0001_initial"),
        ("taggit", "0004_alter_taggeditem_content_type_alter_taggeditem_tag"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="quizinvitation",
            name="inviter",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="quizinvitation",
            name="quiz",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="invitations",
                to="quiz.quiz",
                verbose_name="quiz",
            ),
        ),
        migrations.AddField(
            model_name="quiz",
            name="author",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="quizzes",
                to=settings.AUTH_USER_MODEL,
                verbose_name="author",
            ),
        ),
        migrations.AddField(
            model_name="quiz",
            name="tags",
            field=taggit.managers.TaggableManager(
                help_text="A comma-separated list of tags.",
                through="taggit.TaggedItem",
                to="taggit.Tag",
                verbose_name="Tags",
            ),
        ),
        migrations.AddField(
            model_name="question",
            name="quiz",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="questions",
                to="quiz.quiz",
                verbose_name="quiz",
            ),
        ),
        migrations.AddField(
            model_name="answer",
            name="question",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="answers",
                to="quiz.question",
                verbose_name="question",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="quizinvitation",
            unique_together={("quiz", "email")},
        ),
    ]