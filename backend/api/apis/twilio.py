import datetime
import logging
import pprint
import random
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

HOLD_MUSIC_TRACKS = 4


def sound_path(name):
    return static(f"api/twilio/sounds/{name}.mp3")


def to_pretty_minutes(timedelta):
    minutes = round(max(timedelta.total_seconds() / 60, 0))
    return f"{minutes} minute{'s' if minutes != 1 else ''}"


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


def get_assignment(id) -> Assignment:
    return Assignment.objects.get(id=id)


def update_assignment_stage(call_sid, assignment: Assignment, stage, countdown=None):
    if stage not in Assignment.Stage.values:
        raise Exception(f"Invalid stage: {stage}")
    send_twilio_message(call_sid, stage, countdown)
    if assignment.stage != Assignment.Stage.VERIFIED and stage == Assignment.Stage.VERIFIED:
        assignment.call_started_at = timezone.now()
    assignment.stage = stage
    assignment.save()


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
def hit_outgoing(request, assignment_id: Form[str], call_sid: Form[str], cheat: Form[bool] = False):
    assignment = Assignment.objects.get(amazon_id=assignment_id)
    cheated = cheat and settings.DEBUG

    response = VoiceResponse()
    response.say(
        "Cheated!" if cheated else f"Welcome, {assignment.worker.name}! Are you excited to call the radio show?"
    )
    if cheated or assignment.stage != Assignment.Stage.INITIAL:
        response.redirect(url("hit_outgoing_call", assignment))
    else:
        send_twilio_message(call_sid, Assignment.Stage.INITIAL)
        response.say("First, we'll test your speaker, microphone and your ability to speak English.")
        response.pause(0.5)
        response.redirect(url("hit_outgoing_verify", assignment, first_run=1))
    return response


@api.post("hit/outgoing/{assignment_id}/verify")
def hit_outgoing_verify(
    request, assignment_id, call_sid: Form[str], speech_result: Form[str | None] = None, first_run: bool = False
):
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
            update_assignment_stage(call_sid, assignment, Assignment.Stage.VERIFIED)
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
    )
    gather.say(
        f"{'After the tone, please r' if first_run else 'R'}epeat the following fruits."
        f" {'. '.join(w.title() for w in assignment.words_to_pronounce)}."
    )
    gather.play(sound_path("beep"))
    return response


@api.post("hit/outgoing/{assignment_id}/call")
def hit_outgoing_call(request, assignment_id, call_sid: Form[str]):
    assignment = get_assignment(assignment_id)
    if assignment.stage == Assignment.Stage.INITIAL:
        # Could have come here from cheating, so update status in that case
        update_assignment_stage(call_sid, assignment, Assignment.Stage.VERIFIED)

    response = VoiceResponse()
    dial = response.dial(
        answer_on_bridge=True,
        action=url("hit_outgoing_call_done", assignment),
        caller_id=assignment.worker.caller_id,
    )
    dial.sip(
        f"{settings.TWILIO_SIP_HOST_USERNAME}@{settings.TWILIO_SIP_DOMAIN}",
        status_callback=url("hit_outgoing_callback_answered", assignment),
        status_callback_event="answered completed",
    )
    return response


@api.post("hit/outgoing/{assignment_id}/callback/answered")
def hit_outgoing_callback_answered(request, assignment_id, call_status: Form[str], parent_call_sid: Form[str]):
    assignment = get_assignment(assignment_id)
    if call_status == "in-progress":  # Answered
        update_assignment_stage(parent_call_sid, assignment, Assignment.Stage.CALL, assignment.hit.min_call_duration)
    elif call_status == "completed":
        if assignment.stage in (Assignment.Stage.CALL, Assignment.Stage.VOICEMAIL):
            assignment.stage = Assignment.Stage.DONE
            assignment.save()
    return HttpResponse(status=204)


@api.post("hit/outgoing/{assignment_id}/call/done")
def hit_outgoing_call_done(request, assignment_id, call_sid: Form[str], dial_call_status: Form[str]):
    assignment = get_assignment(assignment_id)

    response = VoiceResponse()

    if dial_call_status == "completed":
        response.redirect(url("hit_outgoing_completed", assignment))

    elif dial_call_status in ("no-answer", "busy"):
        countdown = (assignment.hit.leave_voicemail_after_duration + assignment.call_started_at) - timezone.now()
        response.say("The host of the show is currently taking another call.")
        if countdown > datetime.timedelta(0):
            update_assignment_stage(call_sid, assignment, Assignment.Stage.HOLD, countdown)
            response.say(
                "You must wait for the host to answer your call for at least another"
                f" {to_pretty_minutes(countdown)} until you can leave a voicemail."
            )
            response.play(sound_path(f"hold-music-{random.randint(1, 4)}"))
            response.say("Trying to connect again now.")
            response.redirect(url("hit_outgoing_call", assignment))
        else:
            # TODO do a better job with recordings than twimlet
            update_assignment_stage(call_sid, assignment, Assignment.Stage.VOICEMAIL)
            message = (
                f"Since you have waited {to_pretty_minutes(assignment.hit.leave_voicemail_after_duration)}. You can now"
                " leave a voicemail. After you are done recording, press the 'finish voicemail' button, or stay silent"
                " for a few moments. Afterwards, you may submit this assignment."
            )
            params = {"Email": settings.TWILIO_TWIMLET_VOICEMAIL_EMAIL, "Message": message, "Transcribe": "true"}
            response.redirect(f"http://twimlets.com/voicemail?{urlencode(params)}")

    return response


@api.post("hit/outgoing/{assignment_id}/completed")
def hit_outgoing_completed(request, assignment_id, call_sid: Form[str]):
    response = VoiceResponse()
    response.say("You have successfully completed this assignment. Thanks!")
    response.play(sound_path("fun-music"))
    response.hangup()
    return response
