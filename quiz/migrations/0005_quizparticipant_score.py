# Generated by Django 3.2.12 on 2022-03-28 11:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quiz", "0004_alter_quiz_slug"),
    ]

    operations = [
        migrations.AddField(
            model_name="quizparticipant",
            name="score",
            field=models.PositiveIntegerField(null=True),
        ),
    ]