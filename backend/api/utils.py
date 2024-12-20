import datetime
from functools import cache
import logging
import re

import boto3
from dateutil.parser import parse as dateutil_parse
import geoip2.database

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.formats import date_format as django_date_format

from .constants import LOCATION_UNKNOWN, SIMULATED_PREFIX


underscore_converter_re = re.compile(r"(?<!^)(?=[A-Z])")
depunctuate_words_re = re.compile(r"[^a-z]+")
logger = logging.getLogger(f"calls.{__name__}")


def short_datetime_str(datetime_or_string: datetime.datetime | str):
    if isinstance(datetime_or_string, str):
        datetime_or_string = dateutil_parse(datetime_or_string)
    return django_date_format(timezone.localtime(datetime_or_string), "SHORT_DATETIME_FORMAT")


def is_subsequence(x, y):
    y_iter = iter(y)
    return all(any(x_item == y_item for y_item in y_iter) for x_item in x)


def normalize_words_to_list(s):
    return depunctuate_words_re.sub(" ", s.lower()).split()


def ChoicesCharField(*args, choices, **kwargs):
    return models.CharField(*args, choices=choices, max_length=max(len(v) for v in choices.values), **kwargs)


@cache
def get_mturk_client(*, production):
    if production:
        if settings.DEBUG and settings.ALLOW_MTURK_PRODUCTION_ACCESS:
            logger.warning("Allowing production access as ALLOW_MTURK_PRODUCTION_ACCESS = True")

        if not settings.ALLOW_MTURK_PRODUCTION_ACCESS:
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


def block_or_unblock_worker(amazon_id, *, block=True):
    success = False
    verb = "block" if block else "unblock"
    if amazon_id and not amazon_id.startswith(SIMULATED_PREFIX):
        method = f"{'create' if block else 'delete'}_worker_block"
        kwargs = {"WorkerId": amazon_id}
        if block:
            kwargs["Reason"] = f"Didn't follow instructions properly. Block created at {timezone.now()}."

        for production, client in get_mturk_clients():
            environment = "production" if production else "sandbox"
            try:
                response = getattr(client, method)(**kwargs)
            except Exception:
                logger.exception(f"Error while {verb}ing worker {amazon_id} in {environment}")
            else:
                code = response["ResponseMetadata"]["HTTPStatusCode"]
                if code == 200:
                    success = True  # At least one environment succeeded
                    logger.info(f"{verb.capitalize()}ed worker {amazon_id} in {environment}")
                else:
                    logger.info(f"Bad response code {code} while {verb}ing worker {amazon_id} in {environment}")
    return success


def block_or_unblock_workers(amazon_ids, *, block=True):
    return [block_or_unblock_worker(amazon_id, block=block) for amazon_id in amazon_ids]
