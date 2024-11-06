# Generated by Django 5.1.2 on 2024-10-18 19:22

import datetime
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0008_add_phone_api"),
    ]

    operations = [
        migrations.CreateModel(
            name="CallRecording",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="created at")),
                ("duration", models.DurationField(default=datetime.timedelta(0), verbose_name="duration")),
                ("url", models.URLField(verbose_name="URL")),
                (
                    "caller",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="api.caller"
                    ),
                ),
            ],
            options={
                "verbose_name": "phone call recording",
                "ordering": ("-created_at", "id"),
                "get_latest_by": "created_at",
                "abstract": False,
            },
        ),
    ]