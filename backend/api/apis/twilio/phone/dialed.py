import datetime
import logging
import random

import phonenumbers

from django.conf import settings
from django.http import HttpResponse

from constance import config
from ninja import Form

from ....constants import LOCATION_UNKNOWN, PHONE_MODE_FORWARDING, PHONE_MODE_NO_CALLS, PHONE_MODE_TAKING_CALLS
from ....models import Caller, CallRecording, Topic, Voicemail
from ....twilio import twilio_client
from ..utils import VoiceResponse
from .api import api, url_for


logger = logging.getLogger(f"calls.{__name__}")

HOLD_MUSIC_TRACKS = tuple(f"dialed/hold-music-{i}" for i in range(1, 4))


def get_caller_from_session(request) -> None | Caller:
    if caller_id := request.session.get("caller_id"):
        try:
            return Caller.objects.get(id=caller_id)
        except Caller.DoesNotExist:
            pass
    return None


# Main entrypoint for direct callers
@api.post("dialed/incoming")
def dialed_incoming(
    request,
    caller: Form[str],
    called: Form[str] = None,
    caller_city: Form[str] = None,
    caller_state: Form[str] = None,
    caller_country: Form[str] = None,
):
    # Play greeting (whether taking calls or not)
    response = VoiceResponse()
    twilio_caller = caller
    caller = None

    # If the call is simulated, take the outgoing sip address as the caller id
    if twilio_caller.startswith(f"sip:{settings.TWILIO_SIP_SIMULATE_USERNAME}@") and called.startswith("sip:"):
        twilio_caller = called.removeprefix("sip:").split("@")[0]

    # Make sure the phone number is valid
    try:
        phonenumbers.parse(twilio_caller)
    except phonenumbers.NumberParseException:
        logger.warning(f"Got incoming call from unknown caller: {twilio_caller}! (phone mode: {config.PHONE_MODE})")
    else:
        location = ", ".join(s for s in (caller_city, caller_state, caller_country) if s) or LOCATION_UNKNOWN
        caller, _ = Caller.objects.get_or_create(number=twilio_caller, defaults={"location": location})
        logger.info(f"Got incoming phone call from: {caller} (phone mode: {config.PHONE_MODE})")

    request.session.update({
        "caller_id_display": caller.caller_id if caller else "unknown",
        "caller_id": caller and caller.id,
    })

    response.play("dialed/welcome")
    if config.PHONE_MODE in (PHONE_MODE_TAKING_CALLS, PHONE_MODE_FORWARDING):
        response.play("dialed/taking-calls/welcome")
        if topic := Topic.get_active():
            response.play("dialed/topic-intro")
            response.play(topic.recording.url)
        redirect_url = "dialed_incoming_gather_taking_calls"
    elif config.PHONE_MODE == PHONE_MODE_NO_CALLS:
        response.play("dialed/no-calls/welcome")
        redirect_url = "dialed_incoming_gather_no_calls"

    response.redirect(url_for(redirect_url))
    return response


def process_subscribe_or_unsubscribe_digits(response, caller, digits):
    if caller:
        if not caller.wants_calls and digits == "1":
            response.play("dialed/subscribed")
            caller.wants_calls = True
            caller.save()
            return True
        elif caller.wants_calls and digits == "9":
            response.play("dialed/unsubscribed")
            caller.wants_calls = False
            caller.save()
            return True
    return False


@api.post("dialed/incoming/gather/taking-calls")
def dialed_incoming_gather_taking_calls(request, digits: Form[str] = None, run_number: int = 1):
    response = VoiceResponse()
    # Reset run to 1 every time we get digits
    if digits:
        run_number = 1
    topic = Topic.get_active()

    # 1 = connects to show (or connects on empty 4th run)
    if digits == "1" or (run_number >= 4 and not digits):
        response.redirect(url_for("dialed_incoming_call"))
        return response

    # 2 = repeats topics
    if topic and digits == "2":
        response.play("dialed/topic-intro")
        response.play(topic.recording.url)

    gather = response.gather(
        action=url_for("dialed_incoming_gather_taking_calls", run_number=run_number + 1),
        num_digits=1,
        action_on_empty_result=True,
        timeout=3,
        finish_on_key="",
    )
    gather.play(f"dialed/taking-calls/greeting/opt-1-call{'-final' if run_number >= 3 else ''}")
    if topic is not None:
        gather.play("dialed/taking-calls/greeting/opt-2-topic")
    gather.play("dialed/opt-pound-repeat")
    gather.play("dialed/taking-calls/greeting/opt-hangup")
    return response


@api.post("dialed/incoming/gather/no-calls")
def dialed_incoming_gather_no_calls(request, digits: Form[str] = None):
    response = VoiceResponse()
    caller = get_caller_from_session(request)

    if digits == "*":
        response.redirect(url_for("dialed_voicemail"))
        return response

    process_subscribe_or_unsubscribe_digits(response, caller, digits)

    if not caller:
        response.play("dialed/no-calls/blocked-caller-id")

    gather = response.gather(num_digits=1, action_on_empty_result=True, finish_on_key="")

    if caller:
        if caller.wants_calls:
            gather.play("dialed/opt-9-unsubscribe")
        else:
            gather.play("dialed/opt-1-subscribe")

    gather.play("dialed/opt-star-voicemail")
    gather.play("dialed/opt-pound-repeat")
    return response


@api.post("dialed/incoming/call")
def dialed_incoming_call(request, call_sid: Form[str]):
    response = VoiceResponse()
    kwargs = {"action": url_for("dialed_incoming_call_done")}

    if config.PHONE_MODE == PHONE_MODE_TAKING_CALLS:
        dial = response.dial(caller_id=request.session["caller_id_display"], **kwargs)
        dial.sip(f"{settings.TWILIO_SIP_HOST_USERNAME}@{settings.TWILIO_SIP_DOMAIN}")
    else:
        dial = response.dial(
            caller_id=settings.TWILIO_OUTGOING_NUMBER,
            record="record-from-answer-dual",
            recording_status_callback=url_for(
                "dial_recording_callback", is_voicemail=False, caller_id=request.session["caller_id"]
            ),
            **kwargs,
        )
        number_kwargs = {}
        if config.ANSWERING_MACHINE_DETECTION:
            number_kwargs.update({
                "machine_detection": "Enable",
                # amd_status_callback seems to want an absolute URL. Created a Twilio help ticket for this.
                "amd_status_callback": url_for(
                    "dial_incoming_call_forward_amd", incoming_call_sid=call_sid, _external=True
                ),
            })
        for number in settings.TWILIO_FORWARD_NUMBERS:
            dial.number(number, **number_kwargs)
    return response


@api.post("dial/incoming/call/forward/amd")
def dial_incoming_call_forward_amd(request, incoming_call_sid: str, answered_by: Form[str]):
    if answered_by == "machine_start":
        logger.info("Forwarding number went to voicemail. Sending call to to dialed_voicemail URL.")
        twiml = VoiceResponse()
        twiml.play("dialed/taking-calls/rejected-voicemail", _external=True)
        twiml.redirect(url_for("dialed_voicemail", _external=True))
        twilio_client.calls(incoming_call_sid).update(twiml=twiml)
    return HttpResponse(status=204)


@api.post("dialed/incoming/call/done")
def dialed_incoming_call_done(request, dial_call_status: Form[str], dial_sip_response_code: Form[int] = None):
    response = VoiceResponse()

    manually_rejected = dial_call_status == "busy" and dial_sip_response_code == 603  # Decline
    rang_but_did_not_answer = dial_call_status == "no-answer" and dial_sip_response_code == 487  # Request Terminated

    if (dial_call_status == "busy" or rang_but_did_not_answer) and not manually_rejected:
        response.redirect(url_for("dialed_incoming_call_busy_gather"))

    elif dial_call_status == "no-answer" or manually_rejected:
        response.play("dialed/taking-calls/rejected-voicemail")
        response.redirect(url_for("dialed_voicemail"))

    elif dial_call_status == "completed":
        response.redirect(url_for("dialed_incoming_call_completed"))

    else:
        logger.warning(f"Got dial_call_status = {dial_call_status}!")
        response.say("An unknown error occurred! Try calling again.")
        response.hangup()

    return response


@api.post("dialed/incoming/call/busy")
def dialed_incoming_call_busy_gather(request, digits: Form[str] = None):
    response = VoiceResponse()

    if digits == "*":
        response.redirect(url_for("dialed_voicemail"))
        return response

    caller = get_caller_from_session(request)

    if process_subscribe_or_unsubscribe_digits(response, caller, digits) or not digits:
        response.play("dialed/taking-calls/busy/opt-hold")

        gather = response.gather(num_digits=1, timeout=0, finish_on_key="")
        if caller:
            if caller.wants_calls:
                gather.play("dialed/opt-star-voicemail")
                gather.play("dialed/opt-9-unsubscribe")
            else:
                gather.play("dialed/taking-calls/busy/opt-1-subscribe")
                gather.play("dialed/opt-star-voicemail")
        gather.play("dialed/opt-pound-repeat")

        if topic := Topic.get_active():
            gather.play("dialed/topic-intro")
            gather.play(topic.recording.url)

        gather.play("dialed/hold-music-throw")
        gather.play(random.choice(HOLD_MUSIC_TRACKS))

    response.redirect(url_for("dialed_incoming_call"))
    return response


@api.post("dialed/incoming/call/completed")
def dialed_incoming_call_completed(request, digits: Form[str] = None):
    response = VoiceResponse()
    caller = get_caller_from_session(request)

    if digits != "1":
        response.play("dialed/thanks")

    process_subscribe_or_unsubscribe_digits(response, caller, digits)
    if caller is not None and not caller.wants_calls:
        gather = response.gather(
            num_digits=1,
            action_on_empty_result=True,
            finish_on_key="",
        )
        gather.play("dialed/opt-1-subscribe")
    else:
        response.play("dialed/goodbye")
        response.play("fun-music")
        response.hangup()
    return response


@api.post("dialed/voicemail")
def dialed_voicemail(request, digits: Form[str] = None):
    response = VoiceResponse()
    topic = Topic.get_active()

    if digits:
        if digits == "#":
            response.play("dialed/voicemail-erased")
        else:
            response.play("dialed/thanks")
            response.play("dialed/goodbye")
            response.play("fun-music")
            response.hangup()
            return response

    if topic is None:
        response.play("dialed/voicemail-intro-no-topic")
    else:
        response.play("dialed/voicemail-intro-topic")
        response.play(topic.recording.url)
    response.play("dialed/voicemail-instructions")
    response.play("beep")

    response.record(
        timeout=15,
        max_length=60 * 5,  # 5 minutes
        recording_status_callback=url_for(
            "dial_recording_callback", is_voicemail=True, caller_id=request.session["caller_id"]
        ),
        play_beep=False,
    )

    return response


@api.post("dialed/recording")
def dial_recording_callback(
    request, recording_duration: Form[int], recording_url: Form[str], is_voicemail: bool = True, caller_id: int = None
):
    try:
        caller = Caller.objects.get(id=caller_id)
    except Caller.DoesNotExist:
        caller = None
    model = Voicemail if is_voicemail else CallRecording
    model.objects.create(url=recording_url, duration=datetime.timedelta(seconds=recording_duration), caller=caller)
    return HttpResponse(status=204)
