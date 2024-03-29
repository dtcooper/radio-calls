import random
import uuid

from django.db import models

from .constants import PRONOUNCER_NUM_WORDS, PRONOUNCER_WORDS
from .utils import match_pronouncer_from_audio_file, max_length_for_choices


MTURK_ID_LENGTH = 255  # From Amazon mturk docs


class HIT(models.Model):
    class Location(models.TextChoices):
        SANDBOX = "sandbox", "Sandbox"
        PRODUCTION = "prod", "Production"
        LOCAL = "local", "Local only (not on Mechanical Turk)"

    id = models.CharField("HIT ID", max_length=MTURK_ID_LENGTH, primary_key=True)
    enabled = models.BooleanField("enabled", default=True)
    created_at = models.DateTimeField("created at", auto_now_add=True, db_index=True)
    topic = models.CharField("topic", max_length=1024)
    location = models.CharField(
        "location",
        choices=Location,
        default=Location.SANDBOX,
        max_length=max_length_for_choices(Location),
    )
    peer_id = models.UUIDField(default=uuid.uuid4)

    def serialize(self):
        return {
            "id": self.id,
            "created_at": self.created_at.replace(microsecond=0),
            "topic": self.topic,
            "peer_id": self.peer_id,
            "location": self.location,
        }

    class Meta:
        verbose_name = "HIT"
        ordering = ("-created_at", "id")
        get_latest_by = "created_at"


class Worker(models.Model):
    id = models.CharField("worker ID", max_length=MTURK_ID_LENGTH, primary_key=True)
    name = models.CharField("name", max_length=40, blank=True)
    peer_id = models.UUIDField(default=uuid.uuid4)


class Assignment(models.Model):
    class Stage(models.IntegerChoices):
        INITIAL = 0, "Handshake completed"
        VERIFIED = 1, "Pronouncer verified"
        COMPLETE = 2, "HIT Complete"

    id = models.CharField("assignment ID", max_length=MTURK_ID_LENGTH, primary_key=True)
    hit = models.ForeignKey(HIT, on_delete=models.CASCADE)
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE)
    stage = models.PositiveSmallIntegerField("stage", default=Stage.INITIAL, choices=Stage)
    pronouncer = models.JSONField("pronouncer")

    def match_pronouncer_from_audio_file(self, path) -> tuple[bool, list[str]]:
        return match_pronouncer_from_audio_file(path, self.pronouncer)

    @staticmethod
    def generate_pronouncer():
        words = list(PRONOUNCER_WORDS.keys())
        return random.sample(words, PRONOUNCER_NUM_WORDS)

    @classmethod
    def from_api(cls, id, hit, worker):
        return cls.objects.update_or_create(
            id=id,
            defaults={
                "hit": hit,
                "worker": worker,
                "pronouncer": cls.generate_pronouncer(),
                "stage": cls.Stage.INITIAL,
            },
        )[0]
