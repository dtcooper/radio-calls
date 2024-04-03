# Generated by Django 5.0.3 on 2024-04-03 14:54

import datetime
import django.core.validators
import django.db.models.deletion
import django_countries.fields
import django_jsonform.models.fields
import uuid
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Worker",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "amazon_id",
                    models.CharField(
                        help_text="Identifier as used by the Amazon MTurk API",
                        max_length=255,
                        null=True,
                        unique=True,
                        verbose_name="Amazon ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="created at")),
                ("name", models.CharField(blank=True, max_length=40, verbose_name="name")),
                (
                    "gender",
                    models.CharField(
                        choices=[("male", "Male"), ("female", "Female"), ("other", "Other")],
                        default="male",
                        max_length=6,
                        verbose_name="gender",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="HIT",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "amazon_id",
                    models.CharField(
                        help_text="Identifier as used by the Amazon MTurk API",
                        max_length=255,
                        null=True,
                        unique=True,
                        verbose_name="Amazon ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="created at")),
                (
                    "name",
                    models.CharField(
                        help_text="Not sent to workers. For internal cataloging.", max_length=100, verbose_name="name"
                    ),
                ),
                (
                    "topic",
                    models.CharField(
                        help_text="Question or topic that users get prompted for.",
                        max_length=1024,
                        verbose_name="topic",
                    ),
                ),
                (
                    "show_host",
                    models.CharField(
                        help_text="The name of the host(s) to be presenter to the workers to call.",
                        max_length=255,
                        verbose_name="host name(s)",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("sandbox", "Sandbox (published)"),
                            ("prod", "Production (published)"),
                            ("local", "Local (unpublished)"),
                        ],
                        default="local",
                        max_length=7,
                        verbose_name="status",
                    ),
                ),
                (
                    "title",
                    models.CharField(help_text="Title as it displays on MTurk.", max_length=1024, verbose_name="title"),
                ),
                (
                    "description",
                    models.CharField(
                        help_text="Description as it displays on MTurk.", max_length=1024, verbose_name="description"
                    ),
                ),
                (
                    "keywords",
                    models.CharField(
                        help_text="Keywords as they display on MTurk.", max_length=1024, verbose_name="keywords"
                    ),
                ),
                (
                    "unique_request_token",
                    models.UUIDField(default=uuid.uuid4, help_text="Token to prevent double submission to MTurk."),
                ),
                (
                    "submitted_at",
                    models.DateTimeField(default=None, help_text="Submission time of this HIT to MTurk.", null=True),
                ),
                (
                    "duration",
                    models.DurationField(
                        help_text=(
                            "Duration of HITs validity. NOTE: workers who accept the HIT at the last minute, can hold"
                            " it for up to the assignment's duration after expiry."
                        ),
                        validators=[
                            django.core.validators.MinValueValidator(datetime.timedelta(seconds=30)),
                            django.core.validators.MaxValueValidator(datetime.timedelta(days=365)),
                        ],
                        verbose_name="HIT duration",
                    ),
                ),
                (
                    "min_call_duration",
                    models.DurationField(
                        default=datetime.timedelta(seconds=120),
                        help_text="After this amount of call time, a worker can submit an assignment.",
                        validators=[
                            django.core.validators.MinValueValidator(datetime.timedelta(seconds=30)),
                            django.core.validators.MaxValueValidator(datetime.timedelta(seconds=3600)),
                        ],
                        verbose_name="minimum call duration",
                    ),
                ),
                (
                    "leave_voicemail_after_duration",
                    models.DurationField(
                        default=datetime.timedelta(seconds=900),
                        help_text=(
                            'After this amount of time of being on "hold" the worker can submit the assignment with a'
                            " voicemail."
                        ),
                        validators=[
                            django.core.validators.MinValueValidator(datetime.timedelta(seconds=30)),
                            django.core.validators.MaxValueValidator(datetime.timedelta(seconds=3600)),
                        ],
                        verbose_name="duration to leave a voicemail after",
                    ),
                ),
                (
                    "approval_code",
                    models.UUIDField(
                        default=uuid.uuid4, help_text="Approval code needed by workers to submit assignment."
                    ),
                ),
                (
                    "approval_delay",
                    models.DurationField(
                        default=datetime.timedelta(days=2),
                        help_text="After this time, an approved assignment will be automatically approved.",
                        validators=[
                            django.core.validators.MinValueValidator(datetime.timedelta(seconds=30)),
                            django.core.validators.MaxValueValidator(datetime.timedelta(days=365)),
                        ],
                    ),
                ),
                (
                    "assignment_duration",
                    models.DurationField(
                        help_text="Amount of time worker has to complete an individual assignment.",
                        validators=[
                            django.core.validators.MinValueValidator(datetime.timedelta(seconds=30)),
                            django.core.validators.MaxValueValidator(datetime.timedelta(days=365)),
                        ],
                        verbose_name="assignment duration",
                    ),
                ),
                (
                    "assignment_number",
                    models.PositiveIntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(500),
                        ],
                        verbose_name="maximum number of assignments",
                    ),
                ),
                (
                    "assignment_reward",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="In dollars, before fees. (See cost estimate before submitting.)",
                        max_digits=4,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.01")),
                            django.core.validators.MaxValueValidator(Decimal("99.99")),
                        ],
                        verbose_name="assignment reward",
                    ),
                ),
                (
                    "qualification_masters",
                    models.BooleanField(
                        default=False,
                        help_text=(
                            "Worker qualification. When enabled only workers with the 'Masters' qualification can do"
                            " this HIT."
                        ),
                        verbose_name="masters qualification",
                    ),
                ),
                (
                    "qualification_num_previously_approved",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Worker qualification. Set to 0 to disable.",
                        verbose_name="assignments previously approved",
                    ),
                ),
                (
                    "qualification_approval_rate",
                    models.PositiveIntegerField(
                        default=0,
                        help_text=(
                            "Worker qualification. Worker's assignment approval rate qualification. Set to 0 to"
                            " disable."
                        ),
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(100),
                        ],
                        verbose_name="approval rate (percentage)",
                    ),
                ),
                (
                    "qualification_countries",
                    django_countries.fields.CountryField(
                        blank=True,
                        default=(
                            "AG",
                            "AU",
                            "BS",
                            "BB",
                            "BZ",
                            "CA",
                            "DM",
                            "GD",
                            "GY",
                            "IE",
                            "JM",
                            "MT",
                            "NZ",
                            "KN",
                            "LC",
                            "VC",
                            "ZA",
                            "TT",
                            "GB",
                            "US",
                        ),
                        help_text=(
                            "Worker qualification. Limit workers to these countries. Leave blank to allow any and all"
                            " countries."
                        ),
                        max_length=746,
                        multiple=True,
                        verbose_name="countries",
                    ),
                ),
                (
                    "qualification_adult",
                    models.BooleanField(
                        default=False,
                        help_text="Worker qualification. Enable to require workers over 18",
                        verbose_name="adult qualification",
                    ),
                ),
                (
                    "publish_api_exception",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text=(
                            "The last contains of the last error (if any) that occurred while publishing this HIT to"
                            " MTurk"
                        ),
                        verbose_name="error details",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
            options={
                "verbose_name": "HIT",
                "ordering": ("-created_at", "id"),
                "get_latest_by": "created_at",
            },
        ),
        migrations.CreateModel(
            name="Assignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "amazon_id",
                    models.CharField(
                        help_text="Identifier as used by the Amazon MTurk API",
                        max_length=255,
                        null=True,
                        unique=True,
                        verbose_name="Amazon ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="created at")),
                (
                    "stage",
                    models.CharField(
                        choices=[
                            ("initial", "Handshake completed"),
                            ("verified", "Verified"),
                            ("hold", "Hold loop"),
                            ("in-progress", "Call in progress"),
                            ("completed", "Call completed"),
                            ("voicemail", "Left voicemail"),
                            ("done", "HIT Complete"),
                        ],
                        default="initial",
                        max_length=11,
                        verbose_name="stage",
                    ),
                ),
                (
                    "call_started_at",
                    models.DateTimeField(blank=True, default=None, null=True, verbose_name="call started at"),
                ),
                ("words_to_pronounce", django_jsonform.models.fields.JSONField()),
                ("hit", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="api.hit")),
                ("worker", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="api.worker")),
            ],
            options={
                "ordering": ("-created_at", "id"),
                "get_latest_by": "created_at",
            },
        ),
    ]
