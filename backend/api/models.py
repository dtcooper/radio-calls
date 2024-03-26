from django.db import models

from .utils import max_length_for_choices


class HIT(models.Model):
    class Location(models.TextChoices):
        SANDBOX = "sandbox", "Sandbox"
        PRODUCTION = "prod", "Production"
        LOCAL = "local", "Local only (not on Mechanical Turk)"

    id = models.CharField("HIT ID", max_length=128, primary_key=True)
    enabled = models.BooleanField("enabled")
    created_at = models.DateTimeField("created at", auto_now_add=True, db_index=True)
    topic = models.TextField("topic")
    location = models.CharField(
        "location",
        choices=Location,
        default=Location.SANDBOX,
        max_length=max_length_for_choices(Location),
    )
    # approval_token = uuid

    class Meta:
        db_table = "hits"
        verbose_name = "HIT"
        ordering = ("-created_at", "id")
        get_latest_by = "created_at"
