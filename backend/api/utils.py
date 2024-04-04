from functools import cache
import json
import logging
import re

import boto3
from twilio.rest import Client as TwilioClient

from django.conf import settings
from django.db import models

from ninja.parser import Parser
from ninja.renderers import BaseRenderer


underscore_converter_re = re.compile(r"(?<!^)(?=[A-Z])")
depunctuate_words_re = re.compile(r"[^a-z]+")
twilio_client = TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
logger = logging.getLogger("django")


class TwiMLRenderer(BaseRenderer):
    media_type = "text/xml"

    # Accepts twilio's VoiceReponse
    def render(self, request, data, *, response_status):
        response = str(data)

        if settings.DEBUG:
            import xml.dom.minidom  # No need to import in production

            response = xml.dom.minidom.parseString(response).toprettyxml(indent=" " * 4)
            logger.info(f"Responding to {request.path} with\n{response}")

        return response


class TwilioParser(Parser):
    # Converts PascalCase and camelCase to Pythonic underscores
    def parse_querydict(self, data, list_fields, request):
        result = super().parse_querydict(data, list_fields, request)
        return {underscore_converter_re.sub("_", k).lower(): v for k, v in result.items()}


def send_twilio_message(call_sid, stage, countdown=None):
    if countdown is not None:
        countdown = max(round(countdown.total_seconds()), 0)

    try:
        twilio_client.calls(call_sid).user_defined_messages.create(
            content=json.dumps({"stage": stage, "countdown": countdown})
        )
    except Exception:
        logger.exception("send_twilio_message() threw an exception! Recovering from the error.")


def is_subsequence(x, y):
    y_iter = iter(y)
    return all(any(x_item == y_item for y_item in y_iter) for x_item in x)


def normalize_words(s):
    return depunctuate_words_re.sub(" ", s.lower()).split()


def ChoicesCharField(*args, choices, **kwargs):
    return models.CharField(*args, choices=choices, max_length=max(len(v) for v in choices.values), **kwargs)


@cache
def get_mturk_client(*, production=False):
    if production:
        raise Exception("XXX production disabled for now!")

    kwargs = {}
    if not production:
        kwargs["endpoint_url"] = "https://mturk-requester-sandbox.us-east-1.amazonaws.com"

    return boto3.client(
        "mturk",
        region_name="us-east-1",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        **kwargs,
    )


def get_mturk_available_balance(*, production=False):
    return get_mturk_client(production).get_account_balance()["AvailableBalance"]
