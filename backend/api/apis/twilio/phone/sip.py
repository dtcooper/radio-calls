import logging

import phonenumbers

from django.conf import settings
from django.http import HttpResponse

from constance import config
from ninja import Form

from ....constants import LOCATION_UNKNOWN
from ....models import Caller
from ....twilio import twilio_client
from ..utils import VoiceResponse
from .api import api, url_for


logger = logging.getLogger(f"calls.{__name__}")


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


@api.post("sip/outgoing/host")
def sip_outgoing_host(
    request, call_sid: Form[str], called: Form[str], digits: Form[str] = None, called_override: str = None
):
    response = VoiceResponse()
    called = (called_override or called).removeprefix("sip:").split("@")[0].split(".")[0].lower()
    simulated = called == "simulate"

    if not simulated:
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

    if not simulated and caller is None:
        if digits == "1":
            caller, _ = Caller.objects.get_or_create(number=called, defaults={"location": LOCATION_UNKNOWN})
            response.say("Created caller entry.")
        else:
            gather = response.gather(num_digits=1, timeout=3, action_on_empty_result=True, finish_on_key="")
            gather.say("Caller does not exist in database. Press 1 to create them and continue.")

    if simulated or caller is not None:
        simulated_or_wants_calls = simulated or caller.wants_calls
        if simulated:
            name_padded = " simulated"
        else:
            name_padded = f" {caller.name}" if caller.name else ""

        if (simulated_or_wants_calls and digits == "1") or digits == "2":
            consent_flow = digits == "1"
            with_answering_machine_detection = not simulated and consent_flow and config.ANSWERING_MACHINE_DETECTION
            logger.info(f"Calling {caller} {consent_flow=} {with_answering_machine_detection=}")

            response.say(f"Calling{name_padded} {'with consent flow' if consent_flow else 'directly'}.")
            dial = response.dial(
                timeout=40,
                caller_id=settings.TWILIO_OUTGOING_NUMBER,
                action=url_for("sip_outgoing_host_done", with_amd=with_answering_machine_detection),
            )

            kwargs = {}
            if consent_flow:
                kwargs["url"] = url_for("sip_outgoing_host_whisper")
                if with_answering_machine_detection:
                    kwargs.update({
                        "machine_detection": "DetectMessageEnd",
                        # amd_status_callback seems to want an absolute URL. Created a Twilio help ticket for this.
                        "amd_status_callback": url_for("sip_outgoing_host_amd", host_call_sid=call_sid, _external=True),
                    })
            if simulated:
                dial.sip(f"{settings.TWILIO_SIP_SIMULATE_USERNAME}@{settings.TWILIO_SIP_DOMAIN}", **kwargs)
            else:
                dial.number(str(caller.number), **kwargs)
            return response

        elif digits == "*":
            if simulated:
                response.say("Would unsubscribe simulated caller.")
            else:
                caller.wants_calls = not caller.wants_calls
                caller.save()
                response.say(f"Now {'' if caller.wants_calls else 'un'}subscribed.")

        gather = response.gather(num_digits=1, timeout=3, action_on_empty_result=True, finish_on_key="")
        if simulated_or_wants_calls:
            gather.say(f"Caller{name_padded} subscribes to incoming calls.")
            gather.say("Press 1 to call with consent flow.")
        else:
            gather.say(f"Warning. Caller{name_padded} does not subscribe to incoming calls!")
        gather.say("Press 2 to call directly.")
        gather.say(f"Press star to {'un' if simulated_or_wants_calls else ''}subscribe caller to incoming calls.")

    return response


@api.post("sip/outgoing/host/whisper")
def sip_outgoing_host_whisper(
    request,
    parent_call_sid: Form[str],
    digits: Form[str] = None,
    more_options: bool = False,
    run_number: int = 0,
):
    # # 1. David and Tony are live on the air right now talking about <topic>
    # # * To connect to the show, press 1 or stay on the line
    # # * To leave a voicemail, press 2
    # # * Un-enroll, press 3
    # # * To repeat this message press *
    # # * If you don't want to talk to David and Tony right now. Hangup now.

    response = VoiceResponse()
    run_number = run_number + 1

    if digits == "1":
        # TODO VOICE WORK
        response.say("Now connecting.")
        return response

    elif not more_options and digits == "#":
        run_number = 1
        more_options = True

    if run_number >= 5:
        response.hangup()
        return response

    gather = response.gather(
        action=url_for("sip_outgoing_host_whisper", more_options=more_options, run_number=run_number),
        num_digits=1,
        timeout=3 if more_options else 1,
        action_on_empty_result=True,
        finish_on_key="",
    )

    if more_options:
        # TODO VOICE WORK
        gather.say("More options.")
    else:
        # TODO VOICE WORK
        gather.say(
            "Incoming call from The Last Show with David Cooper. Press 1 to accept. Press pound for more options."
        )
    return response


@api.post("sip/outgoing/host/done")
def sip_outgoing_host_done(request, with_amd: bool, dial_call_status: Form[str]):
    response = VoiceResponse()
    if dial_call_status == "busy":
        response.say("Caller was busy.")
    elif dial_call_status == "no-answer":
        response.say("Caller did not answer.")
    elif dial_call_status == "complete" and with_amd:
        response.pause(3)  # Give 3 secs for call to be notified by answering machine detection endpoint
    response.hangup()
    return response


@api.post("sip/outgoing/host/amd")
def sip_outgoing_host_amd(request, host_call_sid: str, call_sid: Form[str], answered_by: Form[str]):
    if answered_by.startswith("machine"):
        twiml = VoiceResponse()
        # TODO VOICE WORK
        twiml.say("Oh. I got your mail box. This is the Last Show with David Cooper. TODO REST OF MESSAGE.")
        twiml.play("fun-music", _external=True)
        twilio_client.calls(call_sid).update(twiml=twiml)
        logger.info(f"Updated call {call_sid} with voicemail audio")

        twiml = VoiceResponse()
        twiml.say("Call sent to voicemail.")
        twilio_client.calls(host_call_sid).update(twiml=twiml)
        logger.info(f"Updated host call {host_call_sid} to notify about voicemail")
    return HttpResponse(status=204)
