import datetime
from decimal import Decimal
import logging
import pprint
import random
import traceback
from urllib.parse import urlencode
import uuid

from faker import Faker

from django.conf import settings
from django.contrib.auth.models import User
from django.core import validators
from django.db import models
from django.template.loader import render_to_string
from django.utils import timezone

from django_countries.fields import CountryField
from django_jsonform.models.fields import JSONField

from .constants import (
    ENGLISH_SPEAKING_COUNTRIES,
    MTURK_ID_LENGTH,
    NAME_MAX_LENGTH,
    NUM_WORDS_WORDS_TO_PRONOUNCE,
    QID_ADULT,
    QID_COUNTRY,
    QID_MASTERS_PRODUCTION,
    QID_MASTERS_SANDBOX,
    QID_NUM_APPROVED,
    QID_PERCENT_APPROVED,
    WORDS_TO_PRONOUNCE,
)
from .utils import ChoicesCharField, get_mturk_client


logger = logging.getLogger("django")


class BaseModel(models.Model):
    amazon_id = models.CharField("Amazon ID", max_length=MTURK_ID_LENGTH, unique=True, null=True)
    created_at = models.DateTimeField("created at", auto_now_add=True, db_index=True)

    class Meta:
        abstract = True


def min_max(min_value, max_value):
    return [validators.MinValueValidator(min_value), validators.MaxValueValidator(max_value)]


duration_validators = min_max(datetime.timedelta(seconds=30), datetime.timedelta(days=365))


class HIT(BaseModel):
    class Status(models.TextChoices):
        SANDBOX = "sandbox", "Sandbox"
        PRODUCTION = "prod", "Production"
        LOCAL = "local", "Local (not submitted)"

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    name = models.CharField("code name", max_length=100, help_text="Not sent to MTurk.")
    enabled = models.BooleanField(default=True)
    topic = models.CharField("topic", max_length=1024)
    status = ChoicesCharField("status", choices=Status, default=Status.LOCAL)
    title = models.CharField("title (on MTurk)", max_length=1024)
    description = models.TextField("description (on MTurk)")
    keywords = models.TextField("keywords (on MTurk)")
    unique_request_token = models.UUIDField(default=uuid.uuid4)
    submitted_at = models.DateTimeField(null=True, default=None)
    duration = models.DurationField("duration of HIT", validators=duration_validators)
    approval_code = models.UUIDField(default=uuid.uuid4)
    approval_delay = models.DurationField(
        default=datetime.timedelta(days=3),
        validators=duration_validators,
        help_text="After this time, an approved assignment will be automatically approved.",
    )
    assignment_duration = models.DurationField("duration of individual assignment", validators=duration_validators)
    assignment_number = models.PositiveIntegerField("maximum number of assignments", validators=min_max(1, 500))
    assignment_reward = models.DecimalField(
        "individual reward for assignment",
        max_digits=4,
        decimal_places=2,
        validators=min_max(Decimal("0.01"), Decimal("99.99")),
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
        help_text="Worker qualification. Limit workers to these countries. Leave blank to disable.",
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

    def get_absolute_url(self):
        return f"/hit/?{urlencode({'dbId': self.id})}"

    def __str__(self):
        return self.name

    def cost(self):
        fees = Decimal("0.20")
        if self.assignment_number >= 10:
            fees += Decimal("0.20")
        if self.qualification_masters:
            fees += Decimal("0.05")
        unit_cost = self.assignment_reward * (1 + fees)
        return (unit_cost * self.assignment_number).quantize(Decimal("0.01"))

    def delete(self, *args, **kwargs):
        if self.amazon_id and self.status in (HIT.Status.SANDBOX, HIT.Status.PRODUCTION):
            client = get_mturk_client(production=self.status == HIT.Status.PRODUCTION)
            try:
                client.delete_hit(HITId=self.amazon_id)
            except Exception:
                logger.exception(f"Got an error deleting HIT {self.amazon_id} from MTurk")
        super().delete(*args, **kwargs)

    def publish_to_mturk(self, production=False):
        client = get_mturk_client(production)
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
                    {"Key": "AnswerKey", "MapEntries": [{"Key": "approval-code", "Values": [str(self.approval_code)]}]},
                    {"Key": "ApproveIfKnownAnswerScoreIsAtLeast", "Values": ["1"]},
                    {"Key": "RejectIfKnownAnswerScoreIsLessThan", "Values": ["1"]},
                    {"Key": "RejectReason", "Values": ["Sorry, we could not approve your submission."]},
                    {"Key": "ExtendIfKnownAnswerScoreIsLessThan", "Values": ["1"]},
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

    class Meta:
        verbose_name = "HIT"
        ordering = ("-created_at", "id")
        get_latest_by = "created_at"


class Worker(BaseModel):
    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"

    name = models.CharField("name", max_length=NAME_MAX_LENGTH, blank=True)
    gender = ChoicesCharField("gender", choices=Gender, default=Gender.MALE)

    def __str__(self):
        return f"{self.name} ({self.get_gender_display()})"

    @classmethod
    def from_api(cls, amazon_id):
        faker = Faker()
        fake_gender = "male" if faker.boolean() else "female"
        fake_name = getattr(faker, f"first_name_{fake_gender}")()
        obj, _ = Worker.objects.get_or_create(amazon_id=amazon_id, defaults={"gender": fake_gender, "name": fake_name})
        return obj


def generate_words_to_pronounce():
    return random.sample(WORDS_TO_PRONOUNCE, NUM_WORDS_WORDS_TO_PRONOUNCE)


class Assignment(BaseModel):
    class Stage(models.TextChoices):
        INITIAL = "initial", "Handshake completed"
        VERIFIED = "verified", "Verified"
        CALL_INITIATED = "call-initiated", "Call initiated"
        CALL_CONNECTED = "call-connected", "Call connected"
        LEFT_VOICEMAIL = "left-voicemail", "Left voicemail"
        CALL_COMPLETED = "call-completed", "Call completed"
        DONE = "done", "HIT Complete"

    hit = models.ForeignKey(HIT, on_delete=models.CASCADE)
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE)
    stage = ChoicesCharField("stage", choices=Stage, default=Stage.INITIAL)
    call_started_at = models.DateTimeField("call started at", default=None, null=True, blank=True)
    words_to_pronounce = JSONField(
        schema={
            "type": "array",
            "items": {"type": "string"},
            "minItems": NUM_WORDS_WORDS_TO_PRONOUNCE,
            "maxItems": NUM_WORDS_WORDS_TO_PRONOUNCE,
            "uniqueItems": True,
        },
    )

    class Meta:
        ordering = ("-created_at", "id")
        get_latest_by = "created_at"

    def __str__(self):
        return f"{self.worker}: {self.hit}"

    @classmethod
    def from_api(cls, amazon_id, hit, worker):
        obj, _ = cls.objects.update_or_create(
            amazon_id=amazon_id,
            defaults={
                "call_started_at": None,
                "hit": hit,
                "stage": cls.Stage.INITIAL,
                "words_to_pronounce": generate_words_to_pronounce(),
                "worker": worker,
            },
        )
        return obj
