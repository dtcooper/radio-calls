import datetime
from decimal import Decimal
from functools import cached_property
import logging
import pprint
import random
import traceback
import uuid

from faker import Faker

from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import AbstractUser
from django.core import validators
from django.db import models
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import slugify

from django_countries.fields import CountryField
from django_jsonform.models.fields import JSONField

from .constants import (
    ENGLISH_SPEAKING_COUNTRIES,
    LOCATION_UNKNOWN,
    MTURK_ID_LENGTH,
    NUM_WORDS_WORDS_TO_PRONOUNCE,
    QID_ADULT,
    QID_COUNTRY,
    QID_MASTERS_PRODUCTION,
    QID_MASTERS_SANDBOX,
    QID_NUM_APPROVED,
    QID_PERCENT_APPROVED,
    WORDS_TO_PRONOUNCE,
    WORKER_NAME_MAX_LENGTH,
)
from .utils import ChoicesCharField, get_ip_addr, get_location_from_ip_addr, get_mturk_client


logger = logging.getLogger("django")


class User(AbstractUser):
    is_staff = True  # All users are staff

    class Meta:
        verbose_name = "admin"
        verbose_name_plural = "admins"

    def __init__(self, *args, **kwargs):
        kwargs.pop("is_staff", None)
        super().__init__(*args, **kwargs)


class BaseModel(models.Model):
    amazon_id = models.CharField(
        "Amazon ID",
        max_length=MTURK_ID_LENGTH,
        unique=True,
        null=True,
        help_text="Identifier as used by the Amazon MTurk API",
    )
    created_at = models.DateTimeField("created at", auto_now_add=True, db_index=True)

    class Meta:
        abstract = True


def min_max(min_value, max_value):
    return [validators.MinValueValidator(min_value), validators.MaxValueValidator(max_value)]


duration_validators = min_max(datetime.timedelta(seconds=30), datetime.timedelta(days=365))
call_duration_validators = min_max(datetime.timedelta(seconds=30), datetime.timedelta(minutes=60))


class HIT(BaseModel):
    CLONE_PREFIX = "Clone of "
    CLONE_FIELDS = (
        "approval_delay",
        "assignment_duration",
        "assignment_number",
        "assignment_reward",
        "description",
        "duration",
        "keywords",
        "leave_voicemail_after_duration",
        "min_call_duration",
        "qualification_adult",
        "qualification_approval_rate",
        "qualification_countries",
        "qualification_masters",
        "qualification_num_previously_approved",
        "show_host",
        "title",
        "topic",
    )

    class Status(models.TextChoices):
        SANDBOX = "sandbox", "Sandbox (published)"
        PRODUCTION = "prod", "Production (published)"
        LOCAL = "local", "Unpublished (local only)"

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    name = models.CharField("name", max_length=100, help_text="Not sent to workers. For internal cataloging.")
    topic = models.CharField("topic", max_length=1024, help_text="Question or topic that users get prompted for.")
    show_host = models.CharField(
        "host name(s)", max_length=255, help_text="The name of the host(s) to be presenter to the workers to call."
    )
    status = ChoicesCharField("status", choices=Status, default=Status.LOCAL)
    title = models.CharField("title", max_length=1024, help_text="Title as it displays on MTurk.")
    description = models.CharField("description", max_length=1024, help_text="Description as it displays on MTurk.")
    keywords = models.CharField(
        "keywords",
        max_length=1024,
        help_text=(
            'Keywords as they display on MTurk. Examples show these as comma-separated and lowercase, e. g. "one, two,'
            ' three".'
        ),
    )
    unique_request_token = models.UUIDField(
        default=uuid.uuid4, help_text="Token to prevent double submission to MTurk."
    )
    submitted_at = models.DateTimeField(null=True, default=None, help_text="Submission time of this HIT to MTurk.")
    duration = models.DurationField(
        "HIT duration",
        validators=duration_validators,
        help_text=(
            "Duration of HITs validity. NOTE: workers who accept the HIT at the last minute, can hold it for up to"
            " the assignment's duration after expiry."
        ),
    )
    min_call_duration = models.DurationField(
        "minimum call duration",
        default=datetime.timedelta(minutes=3),
        validators=call_duration_validators,
        help_text="After this amount of call time, a worker can submit an assignment.",
    )
    leave_voicemail_after_duration = models.DurationField(
        "duration to leave a voicemail after",
        default=datetime.timedelta(minutes=15),
        validators=call_duration_validators,
        help_text='After this amount of time of being on "hold" the worker can submit the assignment with a voicemail.',
    )
    approval_code = models.UUIDField(
        default=uuid.uuid4, help_text="Approval code needed by workers to submit assignment."
    )
    approval_delay = models.DurationField(
        default=datetime.timedelta(days=2),
        validators=duration_validators,
        help_text="After this time, an approved assignment will be automatically approved.",
    )
    assignment_duration = models.DurationField(
        "assignment duration",
        validators=duration_validators,
        help_text="Amount of time worker has to complete an individual assignment.",
    )
    assignment_number = models.PositiveIntegerField("maximum number of assignments", validators=min_max(1, 500))
    assignment_reward = models.DecimalField(
        "assignment reward",
        max_digits=4,
        decimal_places=2,
        validators=min_max(Decimal("0.01"), Decimal("99.99")),
        help_text="In dollars, before fees. (See cost estimate before submitting.)",
    )
    qualification_masters = models.BooleanField(
        "masters qualification",
        default=False,
        help_text="Worker qualification. When enabled only workers with the 'Masters' qualification can do this HIT.",
    )
    qualification_num_previously_approved = models.PositiveIntegerField(
        "assignments previously approved", default=0, help_text="Worker qualification. Set to 0 to disable."
    )
    qualification_approval_rate = models.PositiveIntegerField(
        "approval rate (percentage)",
        default=0,
        validators=min_max(0, 100),
        help_text="Worker qualification. Worker's assignment approval rate qualification. Set to 0 to disable.",
    )
    qualification_countries = CountryField(
        "countries",
        multiple=True,
        default=ENGLISH_SPEAKING_COUNTRIES,
        blank=True,
        help_text="Worker qualification. Limit workers to these countries. Leave blank to allow any and all countries.",
    )
    qualification_adult = models.BooleanField(
        "adult qualification", default=False, help_text="Worker qualification. Enable to require workers over 18"
    )
    publish_api_exception = models.TextField(
        "error details",
        default="",
        blank=True,
        help_text="The last contains of the last error (if any) that occurred while publishing this HIT to MTurk",
    )

    class Meta:
        verbose_name = "HIT"
        ordering = ("-created_at", "id")
        get_latest_by = "created_at"
        permissions = (
            ("preview_hit", "Can preview HIT (frontend)"),
            ("publish_sandbox_hit", "Can publish HIT to MTurk (Sandbox)"),
            ("publish_production_hit", "Can publish HIT to MTurk (Production)"),
        )

    def __str__(self):
        return f"{self.name} ({self.topic})"

    def clone(self):
        hit = HIT()
        for field in self.CLONE_FIELDS:
            value = getattr(self, field)
            setattr(hit, field, value)
        hit.name = f"{self.CLONE_PREFIX}{self.name}"[: self._meta.get_field("name").max_length]
        hit.save(is_cloning=True)
        hit.refresh_from_db()
        return hit

    def save(self, *args, is_cloning=False, **kwargs):
        if not is_cloning and self.name.startswith(self.CLONE_PREFIX):
            self.name = self.name.removeprefix(self.CLONE_PREFIX)
        super().save(*args, **kwargs)

    def get_cost_estimate(self):
        fees = Decimal("0.20")
        if self.assignment_number >= 10:
            fees += Decimal("0.20")
        if self.qualification_masters:
            fees += Decimal("0.05")
        unit_cost = self.assignment_reward * (1 + fees)
        return (unit_cost * self.assignment_number).quantize(Decimal("0.01"))

    @property
    def is_production(self):
        return self.status == HIT.Status.PRODUCTION

    @property
    def is_published(self):
        return self.status in (HIT.Status.SANDBOX, HIT.Status.PRODUCTION)

    @property
    def is_on_amazon(self):
        return self.amazon_id and self.is_published

    @cached_property
    def __amazon_obj(self) -> dict | None:
        if self.is_on_amazon:
            production = self.is_production
            client = get_mturk_client(production=production)
            try:
                return client.get_hit(HITId=self.amazon_id)["HIT"]
            except Exception:
                logger.exception(f"Error fetching HIT {self.amazon_id} from Amazon ({production=})")
        return None

    @admin.display(description="Amazon status")
    def get_amazon_status(self):
        return self.__amazon_obj["HITStatus"] if self.__amazon_obj else "Not submitted"

    def publish_to_mturk(self, *, production=False):
        client = get_mturk_client(production=production)
        kwargs = {
            "AssignmentDurationInSeconds": int(self.assignment_duration.total_seconds()),
            "AutoApprovalDelayInSeconds": int(self.approval_delay.total_seconds()),
            "Description": self.description,
            "Keywords": self.keywords,
            "LifetimeInSeconds": int(self.duration.total_seconds()),
            "MaxAssignments": self.assignment_number,
            "Question": render_to_string("api/external_question.xml", {"url": f"https://{settings.DOMAIN_NAME}/hit/"}),
            "RequesterAnnotation": f"{self.name} ({self.topic})",
            "Reward": f"{self.assignment_reward:.02f}",
            "Title": self.title,
            "UniqueRequestToken": str(self.unique_request_token),
            "AssignmentReviewPolicy": {
                "PolicyName": "ScoreMyKnownAnswers/2011-09-01",
                "Parameters": [
                    {"Key": "AnswerKey", "MapEntries": [{"Key": "approvalCode", "Values": [str(self.approval_code)]}]},
                    {"Key": "RejectIfKnownAnswerScoreIsLessThan", "Values": ["1"]},
                    {
                        "Key": "RejectReason",
                        "Values": ["You submitted the assignment without first properly completing it."],
                    },
                ],
            },
        }

        qualifications = []
        if self.qualification_masters:
            qualifications.append({
                "QualificationTypeId": QID_MASTERS_PRODUCTION if production else QID_MASTERS_SANDBOX,
                "Comparator": "Exists",
            })
        if self.qualification_approval_rate > 0:
            qualifications.append({
                "QualificationTypeId": QID_PERCENT_APPROVED,
                "Comparator": "GreaterThanOrEqualTo",
                "IntegerValues": [self.qualification_approval_rate],
            })
        if self.qualification_num_previously_approved > 0:
            qualifications.append({
                "QualificationTypeId": QID_NUM_APPROVED,
                "Comparator": "GreaterThanOrEqualTo",
                "IntegerValues": [self.qualification_num_previously_approved],
            })
        if self.qualification_countries:
            qualifications.append({
                "QualificationTypeId": QID_COUNTRY,
                "Comparator": "In",
                "LocaleValues": [{"Country": country.code} for country in self.qualification_countries],
            })
        if self.qualification_adult:
            qualifications.append({
                "QualificationTypeId": QID_ADULT,
                "Comparator": "EqualTo",
                "IntegerValues": [1],
            })
        if qualifications:
            kwargs["QualificationRequirements"] = qualifications

        try:
            response = client.create_hit(**kwargs)
        except Exception:
            self.publish_api_exception = traceback.format_exc()
            logger.exception(f"Error ocurred while publishing to {'Production' if production else 'the Sandbox'}")
            self.save()
            return False

        else:
            if settings.DEBUG:
                logger.info(f"Got response from Amazon...\n{pprint.pformat(response)}")
            self.submitted_at = timezone.now()
            self.amazon_id = response["HIT"]["HITId"]
            self.status = self.Status.PRODUCTION if production else self.Status.SANDBOX
            self.publish_api_exception = ""
            self.save()
            return True


class Worker(BaseModel):
    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"

    name = models.CharField("name", max_length=WORKER_NAME_MAX_LENGTH, blank=True)
    gender = ChoicesCharField("gender", choices=Gender, default=Gender.MALE)
    ip_address = models.GenericIPAddressField("IP address", null=True, default=None, blank=True)
    location = models.CharField(
        "location",
        max_length=384,
        default=LOCATION_UNKNOWN,
        help_text="Physical location (ie, city and country) where worker is located based on IP address",
    )

    def __str__(self):
        return f"{self.name} ({self.get_gender_display()})"

    @property
    def caller_id(self):
        return f"{self.gender[:1].upper()}.{slugify(self.name)}"

    @classmethod
    def from_api(cls, request, amazon_id):
        faker = Faker()
        fake_gender = "male" if faker.boolean() else "female"
        fake_name = getattr(faker, f"first_name_{fake_gender}")()
        ip_addr = get_ip_addr(request)
        obj, _ = Worker.objects.update_or_create(
            amazon_id=amazon_id,
            create_defaults={"gender": fake_gender, "name": fake_name},
            defaults={"location": get_location_from_ip_addr(ip_addr), "ip_address": ip_addr},
        )

        return obj


def generate_words_to_pronounce():
    return random.sample(WORDS_TO_PRONOUNCE, NUM_WORDS_WORDS_TO_PRONOUNCE)


class Assignment(BaseModel):
    class Stage(models.TextChoices):
        # Update HIT.js
        INITIAL = "initial", "Handshake completed"
        VERIFIED = "verified", "Verified"
        HOLD = "hold", "Hold loop"
        CALL = "call", "Call made"
        VOICEMAIL = "voicemail", "HIT complete (voicemail)"
        DONE = "done", "HIT complete (call)"

    hit = models.ForeignKey(HIT, on_delete=models.CASCADE)
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE)
    stage = ChoicesCharField("stage", choices=Stage, default=Stage.INITIAL)
    call_started_at = models.DateTimeField("call started at", default=None, null=True, blank=True)
    call_completed_at = models.DateTimeField("call ended time", default=None, null=True, blank=True)
    words_to_pronounce = JSONField(
        schema={
            "type": "array",
            "items": {"type": "string"},
            "minItems": NUM_WORDS_WORDS_TO_PRONOUNCE,
            "maxItems": NUM_WORDS_WORDS_TO_PRONOUNCE,
            "uniqueItems": True,
        },
    )
    voicemail_duration = models.DurationField("voicemail duration", default=datetime.timedelta(0))
    voicemail_url = models.URLField("voicemail URL", blank=True)

    class Meta:
        ordering = ("-created_at", "id")
        get_latest_by = "created_at"

    def __str__(self):
        return f"{self.worker}: {self.hit}"

    def save(self, *args, **kwargs):
        # Reset call when state set to INITIAL
        if self.stage == self.Stage.INITIAL:
            self.call_started_at = None
        # Start call when stage moved from INITIAL to anything else
        elif self.call_started_at is None:
            self.call_started_at = timezone.now()

        if self.stage == self.Stage.DONE and self.call_completed_at is None:
            self.call_completed_at = timezone.now()

        super().save(*args, **kwargs)

    @cached_property
    def __amazon_obj(self) -> dict | None:
        if self.hit.is_on_amazon:
            production = self.hit.is_production
            client = get_mturk_client(production=production)
            try:
                return client.get_assignment(AssignmentId=self.amazon_id)["Assignment"]
            except Exception:
                logger.exception(f"Error fetching assignment {self.amazon_id} from Amazon ({production=})")
        return None

    @admin.display(description="Amazon status")
    def get_amazon_status(self):
        return self.__amazon_obj["AssignmentStatus"] if self.__amazon_obj else "Not submitted"

    @classmethod
    def from_api(cls, amazon_id, hit, worker, reset_to_initial=False):
        defaults = {
            "call_started_at": None,
            "hit": hit,
            "words_to_pronounce": generate_words_to_pronounce(),
            "worker": worker,
        }
        if reset_to_initial:
            defaults.update({"stage": cls.Stage.INITIAL, "call_started_at": None, "call_completed_at": None})
        obj, _ = cls.objects.update_or_create(amazon_id=amazon_id, defaults=defaults)
        return obj
