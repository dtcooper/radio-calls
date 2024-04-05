from functools import cache
import logging
import re

import boto3
import geoip2.database

from django.conf import settings
from django.db import models

from ninja.parser import Parser
from ninja.renderers import BaseRenderer

from .constants import LOCATION_UNKNOWN


underscore_converter_re = re.compile(r"(?<!^)(?=[A-Z])")
depunctuate_words_re = re.compile(r"[^a-z]+")
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


def send_twilio_message_at_end_of_request(request, call_sid, stage, countdown=None, words_heard=None):
    # Happens after request is processed via middle so any transactions aren't blocked
    request._twilio_user_defined_message = (call_sid, stage, countdown, words_heard)


def is_subsequence(x, y):
    y_iter = iter(y)
    return all(any(x_item == y_item for y_item in y_iter) for x_item in x)


def normalize_words(s):
    return depunctuate_words_re.sub(" ", s.lower()).split()


def ChoicesCharField(*args, choices, **kwargs):
    return models.CharField(*args, choices=choices, max_length=max(len(v) for v in choices.values), **kwargs)


@cache
def get_mturk_client(*, production=False):
    if production and settings.DEBUG:
        raise Exception("Preventing production access when DEBUG = True")

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


def get_ip_addr(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    return x_forwarded_for.split(",")[0] if x_forwarded_for else request.META.get("REMOTE_ADDR")


def get_location_from_ip_addr(ip_addr):
    try:
        with geoip2.database.Reader(settings.GEOIP2_LITE_CITY_DB_PATH) as reader:
            resp = reader.city(ip_addr)
        parts = (resp.city.name, resp.subdivisions.most_specific.name, resp.country.name, resp.continent.name)
        return ", ".join(filter(None, parts)) or LOCATION_UNKNOWN
    except Exception:
        pass

    return LOCATION_UNKNOWN
