import json
import logging
import re

from twilio.rest import Client as TwilioClient

from django.conf import settings

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


def send_twilio_message(parent_call_sid, message):
    try:
        twilio_client.calls(parent_call_sid).user_defined_messages.create(content=json.dumps(message))
    except Exception:
        logger.exception("send_twilio_message() threw an exception!")


def is_subsequence(x, y):
    y_iter = iter(y)
    return all(any(x_item == y_item for y_item in y_iter) for x_item in x)


def normalize_words(s):
    return depunctuate_words_re.sub(" ", s.lower()).split()
