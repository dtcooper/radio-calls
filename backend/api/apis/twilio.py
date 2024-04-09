import datetime
import logging
import pprint
import random
from urllib.parse import urlencode

from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import VoiceResponse

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone

from ninja import Form, NinjaAPI

from ..constants import NUM_VERIFY_TRIES
from ..models import Assignment
from ..utils import TwilioParser, TwiMLRenderer, is_subsequence, normalize_words, send_twilio_message_at_end_of_request


validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
logger = logging.getLogger(f"calls.{__name__}")

# This is what Blink uses (unused, but here for reference)
# SIP_BUSY_CODE = 486
# SIP_REJECT_CODE = 603
# SIP_DONE_CODE = 200

HOLD_MUSIC_TRACKS = 4
CALL = Assignment.CallStep.CALL
DONE = Assignment.CallStep.DONE
HOLD = Assignment.CallStep.HOLD
INITIAL = Assignment.CallStep.INITIAL
VERIFIED = Assignment.CallStep.VERIFIED
VOICEMAIL = Assignment.CallStep.VOICEMAIL


def sound_path(name):
    return static(f"api/twilio/sounds/{name}.mp3")


def to_pretty_minutes(timedelta):
    minutes = round(max(timedelta.total_seconds() / 60, 0))
    return f"{minutes} minute{'s' if minutes != 1 else ''}"


def twilio_auth(request):
    authorized = False
    signature = request.headers.get("X-Twilio-Signature")
    if signature:
        authorized = validator.validate(request.build_absolute_uri(), request.POST, signature)

    if settings.DEBUG:
        if not authorized:
            logger.warning("Request not properly signed from Twilio, but allowing it since DEBUG = True")
            authorized = True
        logger.info(f"Got request to {request.path}...\n{pprint.pformat(dict(request.POST))}")

    return authorized


def get_assignment_atomic(id) -> Assignment:
    return Assignment.objects.select_for_update().get(id=id)


def update_assignment_call_step_and_message_client(
    request, call_sid, assignment: Assignment, call_step, *, countdown=None
):
    if call_step not in Assignment.CallStep.values:
        raise Exception(f"Invalid call_step: {call_step}")

    if call_step != assignment.call_step:
        assignment.append_progress(f"call step {assignment.call_step} > {call_step}")

    assignment.call_step = call_step
    assignment.save()

    send_twilio_message_at_end_of_request(request, call_sid, call_step, countdown)


def url(name, assignment=None, **params):
    kwargs = {}
    if assignment is not None:
        kwargs["assignment_id"] = assignment.id

    url = reverse(f"twilio:{name}", kwargs=kwargs)
    if params:
        url = f"{url}?{urlencode(params)}"
    return url


api = NinjaAPI(
    renderer=TwiMLRenderer(), parser=TwilioParser(), urls_namespace="twilio", auth=twilio_auth, docs_url=None
)


@api.post("sip/incoming")
def sip_incoming(request):
    response = VoiceResponse()
    response.say("Nothing implemented for now!")
    return response


@api.post("hit/outgoing")
@transaction.atomic
def hit_outgoing(request, assignment_id: Form[str], call_sid: Form[str], cheat: Form[bool] = False):
    assignment = Assignment.objects.get(amazon_id=assignment_id)
    cheated = cheat and settings.DEBUG  # Only work in development

    response = VoiceResponse()
    if cheated:
        response.say("Cheating.")
    else:
        response.say(
            f"Welcome, {assignment.worker.name}! Thanks for doing this assignment. Are you excited to call the radio"
            " show?"
        )

    if cheated or assignment.call_step != INITIAL:
        assignment.append_progress("call initiated (skipping verify)")
        response.redirect(url("hit_outgoing_call", assignment))
    else:
        assignment.append_progress("call initiated")
        send_twilio_message_at_end_of_request(request, call_sid, INITIAL)
        response.say("First, we'll test your speaker and microphone and your ability to speak English.")
        response.pause(1)
        response.redirect(url("hit_outgoing_verify", assignment, first_run=1))
    return response


@api.post("hit/outgoing/{assignment_id}/verify")
@transaction.atomic
def hit_outgoing_verify(
    request,
    assignment_id,
    call_sid: Form[str],
    speech_result: Form[str | None] = None,
    first_run: bool = False,
    try_count: int = 1,
):
    assignment = get_assignment_atomic(assignment_id)
    response = VoiceResponse()

    if try_count > NUM_VERIFY_TRIES:
        assignment.append_progress(f"verified hangup - tried {NUM_VERIFY_TRIES} times")
        response.say(
            "We didn't seem to hear anything. Please check that your microphone is working correctly and call again."
        )
        response.hangup()
        return response

    if speech_result:
        words_heard = normalize_words(speech_result)
        match = is_subsequence(assignment.words_to_pronounce, words_heard)
        progress_line = (
            f"expected=[{', '.join(assignment.words_to_pronounce)}], actual=[{', '.join(words_heard)}],"
            f" try_count={try_count - 1}"
        )
        logger.info(f"Got words [{match=}]: {progress_line}")
        if match:
            assignment.append_progress(f"verify succeeded - {progress_line}")
            update_assignment_call_step_and_message_client(request, call_sid, assignment, VERIFIED)
            response.say(
                "That is correct! Well done. You are now being connected to the radio show. The show is hosted by"
                f" {assignment.hit.show_host}. The topic of conversation is: {assignment.hit.topic}."
            )
            response.redirect(url("hit_outgoing_call", assignment))
            return response
        else:
            assignment.append_progress(f"verify failed - {progress_line}")
            # Send back speech result for UI (no need to update status)
            send_twilio_message_at_end_of_request(request, call_sid, INITIAL, words_heard=speech_result)
            response.say("You repeated the words incorrectly. Please try again.")
            response.pause(1)
    elif not first_run:
        send_twilio_message_at_end_of_request(request, call_sid, INITIAL, words_heard="<<<SILENCE>>>")
        assignment.append_progress(f"verify failed - SILENCE, try_count={try_count}")
        response.say("We didn't seem to hear anything. Please check that your microphone is working correctly.")
        response.pause(1)

    if first_run:
        response.say("After the tone, please repeat the following fruits.")
    else:
        response.say("Repeat the following fruits. When you are done, stay silent.")
    response.pause(1)
    response.say(". ".join(w.title() for w in assignment.words_to_pronounce))

    assignment.append_progress("recording verify speech")
    gather = response.gather(
        action_on_empty_result=True,
        action=url("hit_outgoing_verify", assignment, try_count=try_count + 1),
        hints=", ".join(assignment.words_to_pronounce),
        input="speech",
        speech_model="experimental_conversations",
        timeout=4,
        max_speech_time=10,
    )
    gather.play(sound_path("beep"))
    return response


@api.post("hit/outgoing/{assignment_id}/call")
@transaction.atomic
def hit_outgoing_call(request, assignment_id, call_sid: Form[str]):
    assignment = get_assignment_atomic(assignment_id)
    if assignment.call_step == INITIAL:
        # Could have come here from cheating, so update status in that case
        update_assignment_call_step_and_message_client(request, call_sid, assignment, VERIFIED)
    else:
        # Since we're ringing, tell the user that via (but no need to update status)
        send_twilio_message_at_end_of_request(request, call_sid, VERIFIED)

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
@transaction.atomic
def hit_outgoing_callback_answered(request, assignment_id, call_status: Form[str], parent_call_sid: Form[str]):
    assignment = get_assignment_atomic(assignment_id)
    if call_status == "in-progress":  # Answered
        update_assignment_call_step_and_message_client(
            request, parent_call_sid, assignment, CALL, countdown=assignment.hit.min_call_duration
        )
    elif call_status == "completed":
        if assignment.call_step in (CALL, VOICEMAIL):
            # Don't message this to client, they can get to final call_step if call is in
            # CALL or VOICEMAIL status anyway, we get here after a hangup.
            assignment.append_progress("call completed, marked done (probably a hang up)")
            assignment.call_step = DONE
            assignment.save()
        else:
            assignment.append_progress("call completed, not marked done")
    return HttpResponse(status=204)


@api.post("hit/outgoing/{assignment_id}/call/done")
@transaction.atomic
def hit_outgoing_call_done(request, assignment_id, call_sid: Form[str], dial_call_status: Form[str]):
    assignment = get_assignment_atomic(assignment_id)

    response = VoiceResponse()

    if dial_call_status == "completed":
        response.redirect(url("hit_outgoing_completed", assignment))

    elif dial_call_status in ("no-answer", "busy"):
        countdown = (assignment.hit.leave_voicemail_after_duration + assignment.call_started_at) - timezone.now()
        response.say("The host of the show is currently taking another call.")
        if countdown > datetime.timedelta(0):
            assignment.append_progress(f"hold loop, countdown={countdown}")
            update_assignment_call_step_and_message_client(request, call_sid, assignment, HOLD, countdown=countdown)
            response.say(
                f"You must wait for the host to answer your call for at least another {to_pretty_minutes(countdown)},"
                " at which point you can leave a voicemail and submit this assignment. NOTE: The host"
                f" may answer sooner, so you may not have to wait the full {to_pretty_minutes(countdown)}."
            )
            response.play(sound_path("busy-signal"))
            if not settings.DEBUG:
                response.play(sound_path(f"hold-music-{random.randint(1, HOLD_MUSIC_TRACKS)}"))
            response.say("Trying to connect again now.")
            response.redirect(url("hit_outgoing_call", assignment))
        else:
            assignment.append_progress("finished hold loop, allowing voicemail")
            update_assignment_call_step_and_message_client(request, call_sid, assignment, VERIFIED)
            response.say(
                f"Since you have waited {to_pretty_minutes(assignment.hit.leave_voicemail_after_duration)}, you may now"
                " complete this assignment and submit it after leaving a voicemail. After you are done recording,"
                " press the 'finish voicemail' button, or stay silent for a few moments. If you provide a silent"
                " voicemail, your assignment will be rejected."
            )
            response.pause(1)
            response.say("At the tone, please record your message.")
            response.redirect(url("hit_outgoing_voicemail", assignment))

    return response


@api.post("hit/outgoing/{assignment_id}/voicemail")
@transaction.atomic
def hit_outgoing_voicemail(request, assignment_id, call_sid: Form[str]):
    assignment = get_assignment_atomic(assignment_id)
    update_assignment_call_step_and_message_client(request, call_sid, assignment, VOICEMAIL)

    response = VoiceResponse()
    response.record(
        timeout=5,
        maxLength=150,  # 2.5 minutes
        action=url("hit_outgoing_completed", assignment),
        recording_status_callback=url("hit_outgoing_callback_voicemail", assignment),
    )
    response.redirect(url("hit_outgoing_voicemail", assignment))
    return response


@api.post("hit/outgoing/{assignment_id}/callback/voicemail")
@transaction.atomic
def hit_outgoing_callback_voicemail(request, assignment_id, recording_duration: Form[int], recording_url: Form[str]):
    # Callback may come from twilio at any time, causing a race condition, so do this in a transaction
    assignment = get_assignment_atomic(assignment_id)
    assignment.append_progress("voicemail callback")
    assignment.voicemail_url = recording_url
    assignment.voicemail_duration = datetime.timedelta(seconds=recording_duration)
    assignment.save()

    return HttpResponse(status=204)


@api.post("hit/outgoing/{assignment_id}/completed")
@transaction.atomic
def hit_outgoing_completed(request, assignment_id, call_sid: Form[str]):
    assignment = get_assignment_atomic(assignment_id)
    update_assignment_call_step_and_message_client(request, call_sid, assignment, DONE)

    response = VoiceResponse()
    response.say("You have successfully completed this assignment. Thanks!")
    response.play(sound_path("fun-music"))
    response.hangup()
    return response
