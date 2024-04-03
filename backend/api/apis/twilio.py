import logging
import pprint
from urllib.parse import urlencode

from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import VoiceResponse

from django.conf import settings
from django.http import HttpResponse
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone

from ninja import Form, NinjaAPI

from ..models import Assignment
from ..utils import TwilioParser, TwiMLRenderer, is_subsequence, normalize_words, send_twilio_message


validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
logger = logging.getLogger("django")

# This is what Blink uses
SIP_BUSY_CODE = 486
SIP_REJECT_CODE = 603
SIP_DONE_CODE = 200

BUSY_TRACKS = ()


def sound_path(name):
    return static(f"api/twilio/sounds/{name}.mp3")


def twilio_auth(request):
    signed = validator.validate(request.build_absolute_uri(), request.POST, request.headers.get("X-Twilio-Signature"))
    if not signed:
        if settings.DEBUG:
            logger.warning("Request not properly signed from Twilio, but allowing it since DEBUG = True")
        else:
            raise Exception("Request not signed properly from Twilio")

    if settings.DEBUG:
        logger.info(f"Got request to {request.path}...\n{pprint.pformat(dict(request.POST))}")

    return True


def get_assignment(id):
    return Assignment.objects.get(id=id)


def url(name, assignment=None, **params):
    kwargs = {}
    if assignment is not None:
        kwargs["assignment_id"] = assignment.id

    url = reverse(f"twilio:{name}", kwargs=kwargs)
    if params:
        url = f"{url}?{urlencode(params)}"
    return url


api = NinjaAPI(renderer=TwiMLRenderer(), parser=TwilioParser(), urls_namespace="twilio", auth=twilio_auth)


@api.post("sip/incoming")
def sip_incoming(request):
    response = VoiceResponse()
    response.say("Nothing implemented for now!")
    return response


@api.post("hit/outgoing")
def hit_outgoing(request, assignment_id: Form[str], cheat: Form[bool] = False):
    assignment = Assignment.objects.get(amazon_id=assignment_id)
    response = VoiceResponse()

    if cheat and settings.DEBUG:
        logger.warning(f"Cheating for assignment {assignment.id} because DEBUG = True")
        assignment.stage = Assignment.Stage.VERIFIED
        assignment.save()
        response.say("Cheating!")
        response.redirect(url("hit_outgoing_call", assignment))
        return response

    response.say(
        "Welcome Mechanical Turk worker! You're going to call a radio show. First, we'll test your speaker, microphone"
        " and your ability to speak English."
    )
    response.pause(0.5)
    response.redirect(url("hit_outgoing_verify", assignment, first_run=1))
    return response


@api.post("hit/outgoing/{assignment_id}/verify")
def hit_outgoing_verify(request, assignment_id, speech_result: Form[str | None] = None, first_run: bool = False):
    assignment = get_assignment(assignment_id)
    response = VoiceResponse()

    if speech_result is not None:
        words_heard = normalize_words(speech_result)
        match = is_subsequence(assignment.words_to_pronounce, words_heard)
        logger.info(
            f"Got words [{match=}]: expected=[{', '.join(assignment.words_to_pronounce)}]"
            f" actual=[{', '.join(words_heard)}]"
        )
        if match:
            assignment.stage = Assignment.Stage.VERIFIED
            assignment.save()
            response.say(
                "Correct! Well done. You are now being connected to the radio show. The show is hosted by"
                f" {assignment.hit.show_host}. The topic of conversation is {assignment.hit.topic}."
            )
            response.redirect(url("hit_outgoing_call", assignment))
            return response
        else:
            response.say("We didn't hear you correctly. Please try again.")
            response.pause(0.5)
    elif not first_run:
        response.say("We didn't seem to hear anything. Please check your microphone is working correctly.")
        response.pause(0.5)

    gather = response.gather(
        action_on_empty_result=True,
        action=url("hit_outgoing_verify", assignment),
        hints=", ".join(assignment.words_to_pronounce),
        input="speech",
        enhanced=True,
        speech_model="phone_call",
        speech_timeout=3,
        timeout=5,
    )
    gather.say(
        f"{'After the tone, please r' if first_run else 'R'}epeat the following fruits."
        f" {'. '.join(w.title() for w in assignment.words_to_pronounce)}."
    )
    gather.play(sound_path("beep"))
    return response


@api.post("hit/outgoing/{assignment_id}/call")
def hit_outgoing_call(request, assignment_id):
    assignment = get_assignment(assignment_id)
    assignment.call_started_at = timezone.now()
    assignment.stage = Assignment.Stage.VERIFIED
    assignment.save()
    response = VoiceResponse()
    dial = response.dial(
        answer_on_bridge=True,
        action=url("hit_outgoing_call_done", assignment),
        caller_id=assignment.worker.caller_id,
    )
    dial.sip(
        f"{settings.TWILIO_SIP_HOST_USERNAME}@{settings.TWILIO_SIP_DOMAIN}",
        status_callback=url("hit_outgoing_callback_answered", assignment),
        status_callback_event="answered",
    )
    return response


@api.post("hit/outgoing/{assignment_id}/callback/answered")
def hit_outgoing_callback_answered(request, assignment_id, parent_call_sid: Form[str]):
    assignment = get_assignment(assignment_id)
    assignment.stage = assignment.Stage.CALL_IN_PROGRESS
    assignment.save()
    send_twilio_message(parent_call_sid, {"call": "answered"})
    return HttpResponse(status=204)


@api.post("hit/outgoing/{assignment_id}/call/done")
def hit_outgoing_call_done(request, assignment_id, dial_call_status: Form[str]):
    # assignment = get_assignment(assignment_id)

    if dial_call_status == "completed":
        pass

    elif dial_call_status in ("no-answer", "busy"):
        pass  # TODO?! send_twilio_message(parent_call_sid, {"call": "answered"})

    response = VoiceResponse()
    response.say(f"call status {dial_call_status}")
    return response
