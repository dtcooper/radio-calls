from functools import cache
import logging
import re
import traceback

import boto3
import geoip2.database

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.formats import date_format as django_date_format

from ninja.parser import Parser
from ninja.renderers import BaseRenderer

from .constants import LOCATION_UNKNOWN


underscore_converter_re = re.compile(r"(?<!^)(?=[A-Z])")
depunctuate_words_re = re.compile(r"[^a-z]+")
logger = logging.getLogger(f"calls.{__name__}")


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


def send_twilio_message_at_end_of_request(request, call_sid, call_step, countdown=None, words_heard=None):
    # Happens after request is processed via middle so any transactions aren't blocked
    request._twilio_user_defined_message = (call_sid, call_step, countdown, words_heard)


def short_datetime_str(dt):
    return django_date_format(timezone.localtime(dt), "SHORT_DATETIME_FORMAT")


def is_subsequence(x, y):
    y_iter = iter(y)
    return all(any(x_item == y_item for y_item in y_iter) for x_item in x)


def normalize_words(s):
    return depunctuate_words_re.sub(" ", s.lower()).split()


def ChoicesCharField(*args, choices, **kwargs):
    return models.CharField(*args, choices=choices, max_length=max(len(v) for v in choices.values), **kwargs)


@cache
def get_mturk_client(*, production):
    if production and not settings.ALLOW_MTURK_PRODUCTION_ACCESS:
        raise Exception("Preventing production access when ALLOW_MTURK_PRODUCTION_ACCESS = False")

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


def get_mturk_clients():
    environments = (True, False) if settings.ALLOW_MTURK_PRODUCTION_ACCESS else (False,)
    return tuple((env, get_mturk_client(production=env)) for env in environments)


def get_ip_addr(request):
    return request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR")


def get_location_from_ip_addr(ip_addr):
    try:
        with geoip2.database.Reader(settings.GEOIP2_LITE_CITY_DB_PATH) as reader:
            resp = reader.city(ip_addr)
        parts = (resp.city.name, resp.subdivisions.most_specific.name, resp.country.name, resp.continent.name)
        return ", ".join(filter(None, parts)) or LOCATION_UNKNOWN
    except Exception:
        pass

    return LOCATION_UNKNOWN


# For use in ./manage.py shell
def block_workers(amazon_ids, production=True):
    client = get_mturk_client(production=production)
    for amazon_id in amazon_ids:
        try:
            response = client.create_worker_block(
                WorkerId=amazon_id, Reason=f"Didn't follow instructions properly. Block created at {timezone.now()}"
            )
            assert response["ResponseMetadata"]["HTTPStatusCode"] == 200, "Bad response value"
        except Exception:
            print(f"Failed to block {amazon_id}")
            traceback.print_exc()
        else:
            print(f"Blocked {amazon_id}")
