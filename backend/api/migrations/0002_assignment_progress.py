# Generated by Django 5.0.4 on 2024-04-06 17:25

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="assignment",
            old_name="stage",
            new_name="call_step",
        ),
        migrations.AddField(
            model_name="assignment",
            name="progress",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=256), default=list, size=None
            ),
        ),
        migrations.AlterField(
            model_name="assignment",
            name="call_step",
            field=models.CharField(
                choices=[
                    ("initial", "Handshake completed"),
                    ("verified", "Verified"),
                    ("hold", "Hold loop"),
                    ("call", "Call made"),
                    ("voicemail", "HIT complete (voicemail)"),
                    ("done", "HIT complete (call)"),
                ],
                default="initial",
                max_length=9,
                verbose_name="call step",
            ),
        ),
    ]
