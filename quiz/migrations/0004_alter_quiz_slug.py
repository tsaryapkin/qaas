# Generated by Django 3.2.12 on 2022-03-28 05:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quiz", "0003_participantanswer_quizparticipant"),
    ]

    operations = [
        migrations.AlterField(
            model_name="quiz",
            name="slug",
            field=models.SlugField(blank=True, unique=True, verbose_name="slug"),
        ),
    ]
