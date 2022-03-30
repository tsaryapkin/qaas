from django.core.management import call_command
from django.db import migrations

fixture = "initial"


def load_fixture(apps, schema_editor):
    call_command("loaddata", fixture, app_label="quiz")


class Migration(migrations.Migration):

    dependencies = [
        ("quiz", "0009_quizparticipant_notified"),
    ]

    operations = [
        migrations.RunPython(load_fixture),
    ]
