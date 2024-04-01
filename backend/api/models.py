import random

from faker import Faker

from django.db import models


MTURK_ID_LENGTH = 255  # From Amazon mturk docs
NAME_MAX_LENGTH = 40
NUM_WORDS_WORDS_TO_PRONOUNCE = 3
WORDS_TO_PRONOUNCE = ("apple", "lemon", "lime", "mango", "orange", "peach", "pineapple", "watermelon")


def choice_maxlen(choices):
    return max(len(v) for v in choices.values)


class BaseModel(models.Model):
    id = models.SlugField("ID", max_length=MTURK_ID_LENGTH, primary_key=True, blank=False)
    created_at = models.DateTimeField("created at", auto_now_add=True, db_index=True)

    class Meta:
        abstract = True


class HIT(BaseModel):
    class Location(models.TextChoices):
        SANDBOX = "sandbox", "Sandbox"
        PRODUCTION = "prod", "Production"
        LOCAL = "local", "Local only (not on Mechanical Turk)"

    name = models.CharField("code name", max_length=100)
    enabled = models.BooleanField("enabled", default=True)
    topic = models.CharField("topic", max_length=1024)
    location = models.CharField(
        "location",
        choices=Location,
        default=Location.SANDBOX,
        max_length=choice_maxlen(Location),
    )

    def __str__(self):
        return self.name

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
    gender = models.CharField("gender", choices=Gender, default=Gender.MALE, max_length=choice_maxlen(Gender))

    def __str__(self):
        return f"{self.name} ({self.get_gender_display()})"

    @classmethod
    def from_api(cls, id):
        faker = Faker()
        fake_gender = "male" if faker.boolean() else "female"
        fake_name = getattr(faker, f"first_name_{fake_gender}")()
        obj, _ = Worker.objects.get_or_create(id=id, defaults={"gender": fake_gender, "name": fake_name})
        return obj


def generate_words_to_pronounce():
    return random.sample(WORDS_TO_PRONOUNCE, NUM_WORDS_WORDS_TO_PRONOUNCE)


class Assignment(BaseModel):
    class Stage(models.IntegerChoices):
        INITIAL = 0, "Handshake completed"
        VERIFIED = 1, "Verified"
        INITIATED = 2, "Call initiated"
        CONNECTED = 3, "Call connected"
        VOICEMAIL = 4, "Left voicemail"
        COMPLETE = 5, "HIT Complete"

    hit = models.ForeignKey(HIT, on_delete=models.CASCADE)
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE)
    stage = models.PositiveSmallIntegerField("stage", default=Stage.INITIAL, choices=Stage)
    call_started_at = models.DateTimeField("call started at", default=None, null=True, blank=True)
    words_to_pronounce = models.JSONField(default=generate_words_to_pronounce)

    def __str__(self):
        return f"{self.worker}: {self.hit}"

    class Meta:
        ordering = ("-created_at", "id")
        get_latest_by = "created_at"

    @classmethod
    def from_api(cls, id, hit, worker):
        obj, _ = cls.objects.update_or_create(
            id=id,
            defaults={
                "hit": hit,
                "worker": worker,
                "stage": cls.Stage.INITIAL,
                "words_to_pronounce": generate_words_to_pronounce(),
            },
        )
        return obj
