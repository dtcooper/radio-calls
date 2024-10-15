from urllib.parse import urlencode

from django.conf import settings
from django.urls import reverse

from ..utils import create_ninja_api


api = create_ninja_api("phone")


def url_for(name, _external=False, **params):
    url = reverse(f"twilio_phone:{name}")
    if params:
        url = f"{url}?{urlencode(params)}"
    if _external:
        url = f"https://{settings.DOMAIN_NAME}{url}"
    return url
