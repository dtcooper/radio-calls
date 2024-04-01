from django.db import models


MTURK_ID_LENGTH = 255  # From Amazon mturk docs
NAME_MAX_LENGTH = 40


def choice_maxlen(choices):
    return max(len(v) for v in choices.values)


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
        max_length=choice_maxlen(Location),
    )

    def serialize(self):
        return {
            "id": self.id,
            "created_at": self.created_at.replace(microsecond=0),
            "topic": self.topic,
            "location": self.location,
        }

    class Meta:
        verbose_name = "HIT"
        ordering = ("-created_at", "id")
        get_latest_by = "created_at"


class Worker(models.Model):
    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"

    id = models.CharField("worker ID", max_length=MTURK_ID_LENGTH, primary_key=True)
    name = models.CharField("name", max_length=NAME_MAX_LENGTH, blank=True)
    gender = models.CharField("gender", choices=Gender, default=Gender.MALE, max_length=choice_maxlen(Gender))


class Assignment(models.Model):
    class Stage(models.IntegerChoices):
        INITIAL = 0, "Handshake completed"
        VERIFIED = 1, "Verified"
        COMPLETE = 2, "HIT Complete"

    id = models.CharField("assignment ID", max_length=MTURK_ID_LENGTH, primary_key=True)
    hit = models.ForeignKey(HIT, on_delete=models.CASCADE)
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE)
    stage = models.PositiveSmallIntegerField("stage", default=Stage.INITIAL, choices=Stage)

    @classmethod
    def from_api(cls, id, hit, worker):
        return cls.objects.update_or_create(
            id=id,
            defaults={
                "hit": hit,
                "worker": worker,
                "stage": cls.Stage.INITIAL,
            },
        )[0]
