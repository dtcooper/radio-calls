import logging
import random
from urllib.parse import urlencode
import datetime

import phonenumbers

from django.conf import settings
from django.urls import reverse
from django.http import HttpResponse

from constance import config
from ninja import Form

from ...models import Caller, Topic, Voicemail
from .utils import VoiceResponse, create_ninja_api


api = create_ninja_api("phone")
logger = logging.getLogger(f"calls.{__name__}")

HOLD_MUSIC_TRACKS = tuple(f"dialed/hold-music-{i}" for i in range(1, 4))


def url_for(name, **params):
    url = reverse(f"twilio_phone:{name}")
    if params:
        url = f"{url}?{urlencode(params)}"
    return url


@api.post("sip/outgoing")
def sip_outgoing(request, caller: Form[str]):
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


@api.post("sip/outgoing/host")
def sip_outgoing_host(request):
    response = VoiceResponse()
    response.say("sip host")
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

    if twilio_caller.startswith(f"sip:{settings.TWILIO_SIP_SIMULATE_USERNAME}@") and called.startswith("sip:"):
        twilio_caller = called.removeprefix("sip:").split("@")[0]

    try:
        phonenumbers.parse(twilio_caller)
    except phonenumbers.NumberParseException:
        logger.warning(f"Got incoming call from unknown caller: {twilio_caller}!")
    else:
        location = ", ".join(s for s in (caller_city, caller_state, caller_country) if s) or "Unknown"
        caller, _ = Caller.objects.get_or_create(number=twilio_caller, defaults={"location": location})
        logger.info(f"Got incoming phone call from: {caller}")


    taking_calls = config.TAKING_CALLS
    request.session.update({
        "taking_calls": taking_calls,
        "caller_id_display": caller.caller_id if caller else "unknown",
        "caller_id": caller and caller.id,
        "entered_busy_loop_once": False,
        "gather_run_number": 1,
    })

    response.play("dialed/welcome")
    if taking_calls:
        response.play("dialed/taking-calls/welcome")
        topic = Topic.get_active()
        if topic is not None:
            response.play("dialed/topic-intro")
            response.play(topic.recording.url, full_path=True)
    else:
        response.play("dialed/no-calls/welcome")

    response.redirect(url_for("dialed_incoming_gather"))

    return response


# First menu
@api.post("dialed/incoming/gather")
def dialed_incoming_gather(request, digits: Form[str] = None):
    response = VoiceResponse()
    taking_calls = request.session["taking_calls"]
    # Increment every time we don't pass digits
    run_number = request.session["gather_run_number"] = 1 if digits else request.session["gather_run_number"] + 1

    topic = Topic.get_active()

    try:
        caller = Caller.objects.get(id=request.session["caller_id"])
    except Caller.DoesNotExist:
        caller = None

    # Taking calls flow
    #  1. Connect show (or just directly connect after 3 runs)
    #  2. Repeat topic (if it exists)
    if taking_calls:
        # 1 = connects to show (or connects on empty 4th run)
        if digits == "1" or (run_number >= 4 and not digits):
            response.redirect(url_for("dialed_incoming_call"))
            return response

        # 2 = repeats topics
        if topic and digits == "2":
            response.play("dialed/topic-intro")
            response.play(topic.recording.url, full_path=True)

    else:
        # Not taking calls flow
        # Pound (#) - voicemail
        # 1 - subscribe
        # 9 - unsubscribe

        if digits == "*":
            response.redirect(url_for("voicemail"))
            return response

        if caller and not caller.wants_calls and digits == "1":
            response.play("dialed/subscribed")
            caller.wants_calls = True
            caller.save()

        elif caller and caller.wants_calls and digits == "9":
            response.play("dialed/unsubscribed")
            caller.wants_calls = False
            caller.save()

    if not taking_calls and not caller:
        response.play("dialed/no-calls/blocked-caller-id")

    gather = response.gather(num_digits=1, action_on_empty_result=True, finish_on_key="")

    if taking_calls:
        gather.play(f"dialed/taking-calls/greeting/opt-1-call{'-final' if run_number >= 3 else ''}")
        if topic is not None:
            gather.play("dialed/taking-calls/greeting/opt-2-topic")
        gather.play("dialed/opt-pound-repeat")
        gather.play("dialed/taking-calls/greeting/opt-hangup")

    else:
        if caller:
            if caller.wants_calls:
                gather.play("dialed/opt-9-unsubscribe")
            else:
                gather.play("dialed/no-calls/greeting/opt-1-subscribe")

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
        response.say("rejected or offline")
        response.redirect(url_for("voicemail"))

    elif dial_call_status == "completed":
        response.say("completed")

    else:
        response.say("An unknown error occurred! Try calling again.")
        response.hangup()

    return response


@api.post("dialed/incoming/call/busy")
def dialed_incoming_call_busy_gather(request, digits: Form[str] = None):
    response = VoiceResponse()

    if digits == "*":
        response.redirect(url_for("voicemail"))
        return response

    try:
        caller = Caller.objects.get(id=request.session["caller_id"])
    except Caller.DoesNotExist:
        caller = None

    if caller and not caller.wants_calls and digits == "1":
        response.play("dialed/subscribed")
        caller.wants_calls = True
        caller.save()

    elif caller and caller.wants_calls and digits == "9":
        response.play("dialed/unsubscribed")
        caller.wants_calls = False
        caller.save()

    elif not digits:
        response.play("dialed/taking-calls/busy/opt-hold")

        gather = response.gather(num_digits=1, timeout=0, finish_on_key="")
        if caller:
            if caller.wants_calls:
                gather.play("dialed/opt-9-unsubscribe")
            else:
                gather.play("dialed/taking-calls/busy/opt-1-subscribe")
        gather.play("dialed/opt-star-voicemail")
        gather.play("dialed/opt-pound-repeat")

        if request.session["entered_busy_loop_once"]:
            if topic := Topic.get_active():
                gather.play("dialed/topic-intro")
                gather.play(topic.recording.url, full_path=True)

        gather.play("dialed/hold-music-throw")
        gather.play(random.choice(HOLD_MUSIC_TRACKS))

    request.session["entered_busy_loop_once"] = True
    response.redirect(url_for("dialed_incoming_call"))
    return response


@api.post("voicemail")
def voicemail(request):
    response = VoiceResponse()
    topic = Topic.get_active()

    tried_again = request.session.get("voicemail_tried_again", False)
    if tried_again:
        response.play("dialed/voicemail-erased")

    if topic is None:
        response.play("dialed/voicemail-intro-no-topic")
    else:
        response.play("dialed/voicemail-intro-topic")
        response.play(topic.recording.url, full_path=True)
    response.play("dialed/voicemail-instructions")

    response.record(
        timeout=15,
        maxLength=60 * 5,  # 5 minutes
        recording_status_callback=url_for("voicemail_callback", caller_id=request.session["caller_id"]),
        finish_on_key="#",
    )

    request.session["voicemail_tried_again"] = True
    return response


@api.post("voicemail/callback")
def voicemail_callback(request, recording_duration: Form[int], recording_url: Form[str], caller_id: int = None):
    try:
        caller = Caller.objects.get(id=caller_id)
    except Caller.DoesNotExist:
        caller = None
    Voicemail.objects.create(url=recording_url, duration=datetime.timedelta(seconds=recording_duration), caller=caller)
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
