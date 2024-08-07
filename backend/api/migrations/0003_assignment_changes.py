# Generated by Django 5.0.4 on 2024-04-07 20:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0002_assignment_progress"),
    ]

    operations = [
        migrations.AddField(
            model_name="assignment",
            name="call_connected_at",
            field=models.DateTimeField(blank=True, default=None, null=True, verbose_name="call connected at"),
        ),
        migrations.AddField(
            model_name="assignment",
            name="feedback",
            field=models.TextField(blank=True, default="", verbose_name="additional feedback"),
        ),
        migrations.AlterField(
            model_name="assignment",
            name="call_step",
            field=models.CharField(
                choices=[
                    ("initial", "Handshake completed"),
                    ("verified", "Verified"),
                    ("hold", "Hold loop"),
                    ("call", "Call connected"),
                    ("voicemail", "Leaving voicemail"),
                    ("done", "HIT complete (call)"),
                ],
                default="initial",
                max_length=9,
                verbose_name="call step",
            ),
        ),
    ]
