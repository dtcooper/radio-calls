import datetime
import logging
import random
from urllib.parse import urlencode

import phonenumbers

from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse

from constance import config
from ninja import Form

from ...constants import LOCATION_UNKNOWN
from ...models import Caller, Topic, Voicemail
from ...twilio import twilio_client
from .utils import VoiceResponse, create_ninja_api


api = create_ninja_api("phone")
logger = logging.getLogger(f"calls.{__name__}")

HOLD_MUSIC_TRACKS = tuple(f"dialed/hold-music-{i}" for i in range(1, 4))


def url_for(name, _external=False, **params):
    url = reverse(f"twilio_phone:{name}")
    if params:
        url = f"{url}?{urlencode(params)}"
    if _external:
        url = f"https://{settings.DOMAIN_NAME}{url}"
    return url


def get_caller_from_session(request) -> None | Caller:
    if caller_id := request.session.get("caller_id"):
        try:
            return Caller.objects.get(id=caller_id)
        except Caller.DoesNotExist:
            pass
    return None


@api.post("sip/outgoing")
def sip_outgoing(request, caller: Form[str]):
    # Entrypoint for SIP calls
    response = VoiceResponse()
    caller = caller.removeprefix("sip:").split("@")[0]
    if caller in (settings.TWILIO_SIP_HOST_USERNAME, settings.TWILIO_SIP_PICKUP_USERNAME):
        response.redirect(url_for(f"sip_outgoing_{caller}"))
    elif caller == settings.TWILIO_SIP_SIMULATE_USERNAME:
        response.redirect(url_for("dialed_incoming"))
    else:
        response.say("Invalid SIP username.")
        response.hangup()
    return response


@api.post("sip/outgoing/pickup")
def sip_outgoing_pickup(request):
    response = VoiceResponse()
    response.say("sip pickup")
    return response


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
        logger.warning(f"Got incoming call from unknown caller: {twilio_caller}!")
    else:
        location = ", ".join(s for s in (caller_city, caller_state, caller_country) if s) or LOCATION_UNKNOWN
        caller, _ = Caller.objects.get_or_create(number=twilio_caller, defaults={"location": location})
        logger.info(f"Got incoming phone call from: {caller}")

    request.session.update({
        "caller_id_display": caller.caller_id if caller else "unknown",
        "caller_id": caller and caller.id,
    })

    response.play("dialed/welcome")
    if config.TAKING_CALLS:
        response.play("dialed/taking-calls/welcome")
        if topic := Topic.get_active():
            response.play("dialed/topic-intro")
            response.play(topic.recording.url)
        redirect_url = "dialed_incoming_gather_taking_calls"
    else:
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
        response.redirect(url_for("voicemail"))
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
def dialed_incoming_call(request):
    response = VoiceResponse()
    dial = response.dial(action=url_for("dialed_incoming_call_done"), caller_id=request.session["caller_id_display"])
    dial.sip(f"{settings.TWILIO_SIP_HOST_USERNAME}@{settings.TWILIO_SIP_DOMAIN}")
    return response


@api.post("dialed/incoming/call/done")
def dialed_incoming_call_done(request, dial_call_status: Form[str], dial_sip_response_code: Form[int] = None):
    response = VoiceResponse()

    manually_rejected = dial_call_status == "busy" and dial_sip_response_code == 603  # Decline
    rang_but_did_not_answer = dial_call_status == "no-answer" and dial_sip_response_code == 487  # Request Terminated

    if (dial_call_status == "busy" or rang_but_did_not_answer) and not manually_rejected:
        response.redirect(url_for("dialed_incoming_call_busy_gather"))

    elif dial_call_status == "no-answer" or manually_rejected:
        response.play("dialed/taking-calls/rejected-voicemail")
        response.redirect(url_for("voicemail"))

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
        response.redirect(url_for("voicemail"))
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


@api.post("voicemail")
def voicemail(request, digits: Form[str] = None):
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
        recording_status_callback=url_for("voicemail_callback", caller_id=request.session["caller_id"]),
        play_beep=False,
    )

    return response


@api.post("voicemail/callback")
def voicemail_callback(request, recording_duration: Form[int], recording_url: Form[str], caller_id: int = None):
    try:
        caller = Caller.objects.get(id=caller_id)
    except Caller.DoesNotExist:
        caller = None
    Voicemail.objects.create(url=recording_url, duration=datetime.timedelta(seconds=recording_duration), caller=caller)
    return HttpResponse(status=204)


@api.post("sip/outgoing/host")
def sip_outgoing_host(
    request, call_sid: Form[str], called: Form[str], digits: Form[str] = None, called_override: str = None
):
    response = VoiceResponse()
    called = (called_override or called).removeprefix("sip:").split("@")[0].split(".")[0]

    try:
        called = phonenumbers.parse(called, region="US")
    except phonenumbers.NumberParseException:
        response.say(f"Error parsing outgoing number {called}")
        response.hangup()
        return response

    called = phonenumbers.format_number(called, phonenumbers.PhoneNumberFormat.E164)

    caller = None
    try:
        caller = Caller.objects.get(number=called)
    except Caller.DoesNotExist:
        pass

    if caller is None:
        if digits == "1":
            caller, _ = Caller.objects.get_or_create(number=called, defaults={"location": LOCATION_UNKNOWN})
            response.say("Created caller entry.")
        else:
            gather = response.gather(num_digits=1, timeout=3, action_on_empty_result=True, finish_on_key="")
            gather.say("Caller does not exist in database. Press 1 to create them and continue.")

    if caller is not None:
        name_padded = f" {caller.name}" if caller.name else ""

        if (caller.wants_calls and digits == "1") or digits == "2":
            consent = digits == "1"
            response.say(f"Calling{name_padded} {'with consent flow' if consent else 'directly'}.")
            dial = response.dial(timeout=60 if consent else 30, caller_id=settings.TWILIO_NUMBER)
            kwargs = {}
            if consent:
                kwargs["url"] = url_for("sip_outgoing_host_consent_whisper")
                if config.ANSWERING_MACHINE_DETECTION:
                    kwargs.update({
                        "machine_detection": "DetectMessageEnd",
                        # amd_status_callback seems to want an absolute URL. Created a Twilio help ticket for this.
                        "amd_status_callback": url_for("sip_outgoing_host_amd", host_call_sid=call_sid, _external=True),
                    })
            dial.number(str(caller.number), **kwargs)
            if consent and config.ANSWERING_MACHINE_DETECTION:
                response.pause(3)  # Give 3 secs for call to be notified by answering machine detection endpoint
            response.hangup()
            return response

        elif digits == "*":
            caller.wants_calls = not caller.wants_calls
            caller.save()
            response.say(f"Now {'' if caller.wants_calls else 'un'}subscribed.")

        gather = response.gather(num_digits=1, timeout=3, action_on_empty_result=True, finish_on_key="")
        if caller.wants_calls:
            gather.say(f"Caller{name_padded} subscribes to incoming calls.")
            gather.say("Press 1 to call with consent flow.")
        else:
            gather.say(
                f"Warning. Caller {f'{caller.name} ' if caller.name else ''}does not subscribe to incoming calls!"
            )
        gather.say("Press 2 to call directly.")
        gather.say(f"Press star to {'un' if caller.wants_calls else ''}subscribe caller to incoming calls.")

    return response


@api.post("sip/outgoing/host/whisper")
def sip_outgoing_host_consent_whisper(
    request, parent_call_sid: Form[str], digits: Form[str] = None, more_options: bool = False
):
    response = VoiceResponse()
    if digits == "1":
        response.say("Now connecting.")
        return response

    elif not more_options and digits == "#":
        more_options = True

    gather = response.gather(
        action=url_for("sip_outgoing_host_consent_whisper", more_options=more_options),
        num_digits=1,
        timeout=3 if more_options else 1,
        action_on_empty_result=True,
        finish_on_key="",
    )

    if more_options:
        gather.say("More options.")
    else:
        gather.say(
            "Incoming call from The Last Show with David Cooper. Press 1 to accept. Press pound for more options."
        )
    return response


@api.post("sip/outgoing/host/amd")
def sip_outgoing_host_amd(request, host_call_sid: str, call_sid: Form[str], answered_by: Form[str]):
    if answered_by.startswith("machine"):
        twiml = VoiceResponse()
        twiml.say("Oh. I got your mail box. This is the Last Show with David Cooper. TODO REST OF MESSAGE.")
        twiml.play("fun-music", _external=True)
        twilio_client.calls(call_sid).update(twiml=twiml)
        logger.info(f"Updated call {call_sid} with voicemail audio")

        twiml = VoiceResponse()
        twiml.say("Got voicemail of caller.")
        twilio_client.calls(host_call_sid).update(twiml=twiml)
        logger.info(f"Updated host call {host_call_sid} to notify about voicemail")
    return HttpResponse(status=204)


# @api.post("phone/dialed/status")
# def phone_dialed_status(
#     request,
#     caller: Form[str],
#     caller_city: Form[str] = "",
#     caller_state: Form[str] = "",
#     caller_country: Form[str] = None,
# ):
#     response = VoiceResponse()
#     try:
#         phonenumbers.parse(caller)
#     except phonenumbers.NumberParseException:
#         logger.warning(f"Got incoming call from unknown caller: {caller}!")
#     else:
#         location = ", ".join(s for s in (caller_city, caller_state, caller_country) if s) or "Unknown"
#         caller_obj, _ = Caller.objects.get_or_create(number=caller, defaults={"location": location})
#         caller = str(caller_obj).replace(",", "").replace(" ", ".").lower()
#         logger.info(f"Got incoming phone call from: {caller_obj}")

#     try:
#         topic_url = Topic.objects.filter(is_active=True).latest("created_by").recording.url
#     except Topic.DoesNotExist:
#         topic_url = sound_path("no-topic-placeholder")

#     suffix = "taking-calls" if config.TAKING_CALLS else "no-calls"
#     response.play(sound_path(f"welcome-dialed-{suffix}"))

#     response.redirect(
#         twilio_flow_url(
#             caller_id=caller,
#             taking_calls="1" if config.TAKING_CALLS else "0",
#             topic_url=topic_url,
#             topic_intro_url=sound_path("topic-intro"),
#             gather_url=sound_path(f"gather-dialed-{suffix}"),
#             sip_host=f"{settings.TWILIO_SIP_HOST_USERNAME}@{settings.TWILIO_SIP_DOMAIN}",
#         )
#     )
#     return response


# @api.post("phone/dialed/hold-music")
# def phone_dialed_hold_music(request, play_intro: bool = False):
#     # "I know being on hold is annoying... press 1 to leave a message, or stay on hold. We promise we'll get
#     # to you soon"
#     # TODO: rather than directly go into a hold loop
#     response = VoiceResponse()
#     if play_intro:
#         response.play(sound_path("hold-intro"))
#     response.play(sound_path(f"hold-music-{random.randint(1, HOLD_MUSIC_TRACKS)}"))
#     response.redirect(twilio_flow_url())
#     return response


# # Physica

# # Callback
# # 1. David and Tony are live on the air right now talking about <topic>
# # * To connect to the show, press 1 or stay on the line
# # * To leave a voicemail, press 2
# # * Un-enroll, press 3
# # * To repeat this message press *
# # * If you don't want to talk to David and Tony right now. Hangup now.

# # Third state
