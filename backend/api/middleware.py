import json
import logging

from twilio.rest import Client as TwilioClient

from django.conf import settings


twilio_client = TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


logger = logging.getLogger(f"calls.{__name__}")


class SendTwilioUserDefinedMessageAtEndOfRequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request._twilio_user_defined_message = None
        response = self.get_response(request)

        if request._twilio_user_defined_message is not None:
            call_sid, call_step, countdown, words_heard = request._twilio_user_defined_message
            if countdown is not None:
                countdown = max(round(countdown.total_seconds()), 0)

            try:
                twilio_client.calls(call_sid).user_defined_messages.create(
                    content=json.dumps({"callStep": call_step, "countdown": countdown, "wordsHeard": words_heard})
                )
            except Exception:
                logger.exception("send_twilio_message() threw an exception! Recovering from the error.")

        return response
