import hashlib
import os
import random
import re
from urllib.parse import unquote, urlencode

from dotenv import dotenv_values
import requests
from twilio.base.exceptions import TwilioRestException
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from twilio.rest import Client as TwilioClient
from twilio.twiml.messaging_response import MessagingResponse
from twilio.twiml.voice_response import VoiceResponse

from flask import Flask, Response, jsonify, render_template, request, url_for

env = dotenv_values()
AWS_ACCESS_KEY_ID = env["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = env["AWS_SECRET_ACCESS_KEY"]
TWILIO_ACCOUNT_SID = env["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN = env["TWILIO_AUTH_TOKEN"]
TWILIO_API_KEY = env["TWILIO_API_KEY"]
TWILIO_API_SECRET = env["TWILIO_API_SECRET"]
IPSTACK_API_KEY = env["IPSTACK_API_KEY"]
AMAZON_TWIML_APP_SID = env["AMAZON_TWIML_APP_SID"]
DEFAULT_AREA_CODE = env["DEFAULT_AREA_CODE"]
SMS_ADMIN_NUMBER = env["SMS_ADMIN_NUMBER"]
NUMBERS_TO_SIP_ADDRESSES = {env["TIGWIT_NUMBER"]: "tigwit", env["POOLABS_NUMBER"]: "poolabs"}
SIP_ADDRESSES_TO_NUMBERS = {v: k for k, v in NUMBERS_TO_SIP_ADDRESSES.items()}
SIP_ADDRESSES = list(SIP_ADDRESSES_TO_NUMBERS.keys())
SIP_DOMAIN = env["SIP_DOMAIN"]
VOICEMAIL_EMAIL = env["VOICEMAIL_EMAIL"]
MTURK_ADMIN_PASSWORD = env["MTURK_ADMIN_PASSWORD"]

MTURK_BLOCK_HANGUP_SECONDS = 120
AUDIO_NUMBERS_TO_VOICEMAIL = {env["TIGWIT_NUMBER"]: "voicemail", env["POOLABS_NUMBER"]: "poolabs-voicemail"}
AUDIO_HOLD_MUSIC_LIST = tuple(f"hold-music-{n}" for n in range(1, 5))
AUDIO_HOLD_MUSIC_AMAZON = "hold-music-4"
AUDIO_COMPLETED_MUSIC = "completed-music"
AUDIO_NOT_IN_SERVICE = "not-in-service"
AUDIO_BEEP = "beep"

GATHER_WORDS = ("apple", "banana", "orange", "tomato", "lemon", "mango")
with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "worker_alias_words.txt")) as word_file:
    MTURK_WORKER_ALIAS_WORDS = tuple(line.rstrip("\n") for line in word_file.readlines())

HIT_TOPICS = {
    "poop": {
        "code": "poop",
        "name": "poop",
        "emoji": "1F4A9",
        "description": "most recent poop",
        "chart_name": "Bristol Stool Chart",
        "choices": (
            {
                "name": "Type 1: Severe Constipation",
                "description": "Separate hard lumps, like nuts (hard to pass)",
            },
            {
                "name": "Type 2: Mild Constipation",
                "description": "Sausage-shaped but lumpy",
            },
            {
                "name": "Type 3: Normal",
                "description": "Like a sausage but with cracks on its surface",
            },
            {
                "name": "Type 4: Normal",
                "description": "Like a sausage or snake, smooth and soft",
            },
            {
                "name": "Type 5: Lacking Fiber",
                "description": "Soft blobs with clear-cut edges",
            },
            {
                "name": "Type 6: Mild Diarrhea",
                "description": "Mushy consistency with ragged edges",
            },
            {
                "name": "Type 7: Severe Diarrhea",
                "description": "Liquid consistency with no solid pieces",
            },
        ),
    },
    "pool": {
        "code": "pool",
        "name": "swimming",
        "emoji": "1F3CA",
        "description": "favourite way to swim",
        "chart_name": "list of swimming strokes",
        "choices": (
            {
                "name": "Backstroke",
                "description": (
                    "Executed on the back and usually consisting of alternating circular arm pulls and a flutter kick"
                ),
            },
            {
                "name": "Breaststroke",
                "description": (
                    "On one's front, in which the arms are pushed forward and then swept back in a circular movement,"
                    " while the legs are tucked in toward the body and then kicked out in a corresponding movement"
                ),
            },
            {"name": "Freestyle", "description": "Swimming in whatever manner your heart desires"},
            {
                "name": "Butterfly Stroke",
                "description": (
                    "On the chest, with both arms moving symmetrically, accompanied by the butterfly kick (or flutter"
                    " kick)"
                ),
            },
        ),
    },
}


app = Flask(__name__)
if app.env == "development":
    import json
    import pprint
    import xml.dom.minidom

    from werkzeug.middleware.proxy_fix import ProxyFix

    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)

    @app.after_request
    def log_request(response):
        print(" Headers ".center(40, "="))
        pprint.pprint(dict(request.headers))

        if request.method == "POST":
            print(" POST ".center(40, "="))
            pprint.pprint(dict(request.form))

        content_type = response.headers.get("Content-Type")

        if content_type == "text/xml":
            print(" TwiML ".center(40, "="))
            dom = xml.dom.minidom.parseString(response.data)
            print(dom.toprettyxml())
        elif content_type == "application/json":
            print(" JSON ".center(40, "="))
            print(json.dumps(json.loads(response.data), indent=2, sort_keys=True))

        return response


else:
    import logging

    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)


twilio_client = client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def twiml_response(response):
    return Response(str(response), content_type="text/xml")


def sanitize_phone_number(phone_number):
    if phone_number:
        if len(phone_number) == 7 and phone_number.isdigit():
            phone_number = f"{DEFAULT_AREA_CODE}{phone_number}"

        # Replace double zero with plus, because I'm used to that shit!
        for intl_prefix in ("00", "011"):
            if phone_number.startswith(intl_prefix):
                phone_number = "+" + phone_number[len(intl_prefix) :]

        try:
            lookup = twilio_client.lookups.phone_numbers(phone_number).fetch(country_code="US")
        except TwilioRestException:
            pass
        else:
            return lookup.phone_number


def parse_sip_address(address):
    if isinstance(address, str):
        match = re.search(r"^sip:([^@]+)@", address)
        if match:
            return unquote(match.group(1))

    return None


def audio_url(filename, external=False):
    return url_for("static", filename=f"audio/{filename}.mp3", _external=external)


def geoip_lookup():
    geoip_keys = ("country_code", "city", "country_name", "region_name")
    lookup = {}
    lookup = {key.removesuffix("_name"): ("XX" if key.endswith("_code") else "Unknown") for key in geoip_keys}

    if (app.env == "production" or request.args.get("force_geoip")) and not request.args.get("skip_geoip"):
        ip_addr = request.headers.get("X-Forwarded-For") or request.remote_addr
        response = requests.get(f"http://api.ipstack.com/{ip_addr}", params={"access_key": IPSTACK_API_KEY}).json()
        for key in geoip_keys:
            value = response.get(key)
            if value:
                lookup[key.removesuffix("_name")] = value
    return lookup


@app.template_filter("capfirst")
def capfirst(s):
    return f"{s[0].upper()}{s[1:]}"


@app.route("/")
def index():
    return Response("There are forty people in the world and five of them are hamburgers.", content_type="text/plain")


@app.route("/sip-outgoing", methods=("POST",))
def sip_outgoing():
    response = VoiceResponse()

    from_sip = parse_sip_address(request.form["From"])
    from_number = SIP_ADDRESSES_TO_NUMBERS.get(from_sip)
    if from_number:
        to_number = sanitize_phone_number(parse_sip_address(request.form["To"]))
        if to_number:
            response.dial(to_number, answer_on_bridge=True, caller_id=from_number)

        else:
            response.play(audio_url(AUDIO_NOT_IN_SERVICE))
    else:
        response.say("Error. No number for SIP address.")

    return twiml_response(response)


@app.route("/voice-incoming", methods=("POST",))
@app.route("/voice-incoming/<sip_addr>/<from_number>", methods=("POST",))
def voice_incoming(sip_addr=None, from_number=None):
    response = VoiceResponse()
    skip_song = request.args.get("skip_song")

    if sip_addr:  # Coming from Amazon
        to_sip = sip_addr
    else:
        from_number = sanitize_phone_number(request.form["From"])
        to_number = request.form["To"]
        to_sip = NUMBERS_TO_SIP_ADDRESSES.get(to_number)

    if to_sip:
        dial = response.dial(
            answer_on_bridge=True,
            action=url_for("voice_incoming_done", sip_addr=sip_addr, from_number=from_number, skip_song=skip_song),
            caller_id=from_number,
        )
        dial.sip(f"{to_sip}@{SIP_DOMAIN}")
    else:
        response.say("Error. No SIP address for number.")

    return twiml_response(response)


@app.route("/voice-incoming/done", methods=("POST",))
def voice_incoming_done():
    response = VoiceResponse()
    to_number = request.form["To"]
    status = request.form.get("DialCallStatus")
    sip_code = request.form.get("DialSipResponseCode")
    skip_song = request.args.get("skip_song")
    sip_addr = request.args.get("sip_addr")
    from_number = request.args.get("from_number")

    if status == "completed":
        if skip_song:
            response.hangup()
        else:
            response.play(audio_url(AUDIO_COMPLETED_MUSIC))
    elif status == "busy" and sip_code == "486":  # 486 = Busy Here
        if skip_song:  # From Amazon
            hold_music = AUDIO_HOLD_MUSIC_AMAZON
        else:
            hold_music = random.choice(AUDIO_HOLD_MUSIC_LIST)
        response.play(audio_url(hold_music))
        response.redirect(url_for("voice_incoming", sip_addr=sip_addr, from_number=from_number, skip_song=skip_song))
    else:
        audio = AUDIO_NUMBERS_TO_VOICEMAIL.get(to_number)
        message = (
            audio_url(audio, external=True)
            if audio
            else (
                "The radio show can not take your call right now. Please leave a message after the tone. When you are"
                " finished, please press the pound key, or stay silent for a few moments."
            )
        )
        response.redirect(
            "http://twimlets.com/voicemail?"
            + urlencode({"Email": VOICEMAIL_EMAIL, "Message": message, "Transcribe": "true"})
        )

    return twiml_response(response)


@app.route("/sms", methods=("POST",))
def sms():
    from_number = request.form["From"]
    to_number = request.form["To"]
    body = request.form["Body"]

    if from_number == SMS_ADMIN_NUMBER:
        recipient_number = None
        response = MessagingResponse()

        body_split = body.split(None, 1)
        if len(body_split) == 2:
            recipient_number = sanitize_phone_number(body_split[0])
            if recipient_number:
                body = body_split[1]

        if not recipient_number:
            for message in twilio_client.messages.list(limit=100, to=to_number):
                if message.from_ != SMS_ADMIN_NUMBER:
                    recipient_number = message.from_
                    break

        response = MessagingResponse()

        if recipient_number:
            client.messages.create(to=recipient_number, from_=to_number, body=body)
            response.message(f"Sent to {recipient_number} - {body}")
        else:
            response.message("No recipient found! Message not sent.")

        return twiml_response(response)

    else:
        client.messages.create(to=SMS_ADMIN_NUMBER, from_=to_number, body=f"From {from_number} - {body}")
        return Response(status=204)


### Amazon Stuff


@app.route("/amazon/manage")
def amazon_admin():
    if request.authorization and request.authorization.password == MTURK_ADMIN_PASSWORD:
        return render_template(
            "mturk_manage.html", AWS_ACCESS_KEY_ID=AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY=AWS_SECRET_ACCESS_KEY
        )
    else:
        return Response("Access denied", status=401, headers={"WWW-Authenticate": 'Basic realm="Password Protected"'})


@app.route("/amazon/hit")
def amazon_hit():
    force_topic = request.args.get("force_topic")
    custom_topic = request.args.getlist("custom_topic") or None
    assignment_id = request.args.get("assignmentId")
    prompts = request.args.getlist("prompt") or None
    show = request.args.get("show")
    if show not in SIP_ADDRESSES:
        show = "tigwit"

    topic_was_forced = True

    if force_topic == "none":
        topic = None
    elif force_topic in HIT_TOPICS:
        topic = HIT_TOPICS[force_topic]
    elif custom_topic:
        topic = None
        custom_topic = random.choice(custom_topic)
    else:
        topic_was_forced = False
        topic = random.choice(list(HIT_TOPICS.values()))

    return render_template(
        "hit.html",
        assignment_id=assignment_id,
        block_hangup_seconds=MTURK_BLOCK_HANGUP_SECONDS,
        custom_topic=custom_topic,
        debug=bool(request.args.get("debug")),
        development_mode=app.env == "development",
        force_no_browser_support=bool(request.args.get("force_no_browser_support")),
        geoip=geoip_lookup(),
        hit_id=request.args.get("hitId"),
        preview=bool(assignment_id == "ASSIGNMENT_ID_NOT_AVAILABLE"),
        prompts=prompts,
        show=show,
        submit_to=request.args.get("turkSubmitTo"),
        topic=topic,
        topic_was_forced=topic_was_forced,
        worker_id=request.args.get("workerId") or "NO_WORKER_ID",
    )


def get_caller_identity(country_code, worker_id):
    # sip doesn't care about caller IDs from verified phones, so assign this worker a caller based on a "hash" of a
    # unique word mapping to their worker ID and their country
    if worker_id in ("NO_WORKER_ID"):
        worker_alias = "none"
        worker_hash_int = 0
    else:
        worker_hash_int = int(hashlib.sha1(worker_id.encode()).hexdigest(), 16) % len(MTURK_WORKER_ALIAS_WORDS)
        worker_alias = MTURK_WORKER_ALIAS_WORDS[worker_hash_int]

    worker_hash = str(worker_hash_int).zfill(len(str(len(MTURK_WORKER_ALIAS_WORDS) - 1)))
    return worker_alias, f"{country_code}.{worker_alias}.{worker_id}.{worker_hash}"


@app.route("/amazon/token/<country_code>/<worker_id>")
def amazon_token(country_code, worker_id):
    _, identity = get_caller_identity(country_code, worker_id)
    token = AccessToken(TWILIO_ACCOUNT_SID, TWILIO_API_KEY, TWILIO_API_SECRET, identity=identity)
    grant = VoiceGrant(outgoing_application_sid=AMAZON_TWIML_APP_SID)
    token.add_grant(grant)

    return jsonify({"token": token.to_jwt()})


@app.route(
    "/amazon/update-sid/<topic>/<int:choice>/<sip_addr>/<country_code>/<worker_id>/<call_sid>",
    methods=("POST",),
)
def amazon_update_sid(topic, choice, sip_addr, country_code, worker_id, call_sid):
    success = True

    response = VoiceResponse()
    response.say(f"Step {'4' if topic == 'none' else '5'}! You are being connected to the radio show.")
    custom_topic = request.json and request.json.get("custom_topic")
    prompts = request.json and request.json.get("prompts")
    if topic != "none":
        response.say(f"Your {HIT_TOPICS[topic]['description']} is {HIT_TOPICS[topic]['choices'][choice]['name']}.")
    elif custom_topic:
        response.say(f"Please {custom_topic}.")
    if prompts:
        for prompt in prompts:
            response.say(f"{capfirst(prompt)}.")
    response.say("Enjoy your call!")

    worker_alias, from_number = get_caller_identity(country_code, worker_id)
    response.redirect(
        url_for("voice_incoming", sip_addr=sip_addr, from_number=from_number, skip_song="1", _external=True)
    )

    try:
        twilio_client.calls(call_sid).update(twiml=str(response))
    except TwilioRestException:
        success = False

    return jsonify(
        {
            "success": success,
            "caller_id": from_number,
            # Twimlet strips everything but the digits
            "twimlet_caller_id": "".join(c for c in from_number if c.isdigit()),
            "worker_alias": worker_alias,
        }
    )


@app.route("/amazon/voice-request", methods=("POST",))
def amazon_voice_request():
    pin = request.values["AmazonPinCode"]
    topic = request.values["Topic"]
    word = request.args.get("word")
    speech_result = request.form.get("SpeechResult")

    response = VoiceResponse()

    if word:
        if speech_result:
            if word.lower() in filter(None, re.split(r"[^a-z']", speech_result.lower())):
                response.say(
                    f"Correct! Please press the button that says Ready for Step {'3' if topic == 'none' else '4'}."
                )
                response.redirect(url_for("amazon_voice_request_pin", AmazonPinCode=pin, Topic=topic))
                return twiml_response(response)
            else:
                response.say("Incorrect word. Try again.")
        else:
            response.say("Incorrect. Are you sure that your microphone is working? Try again.")
    else:
        word = random.choice(GATHER_WORDS)
        response.say(f"Step {'2' if topic == 'none' else '3'}!")
        response.pause(1)

    response.say(f"Your word is {word}.")

    gather = response.gather(
        action_on_empty_result=True,
        action=url_for("amazon_voice_request", AmazonPinCode=pin, Topic=topic, word=word),
        hints=", ".join(GATHER_WORDS),
        input="speech",
        speech_model="numbers_and_commands",
        speech_timeout="auto",
        timeout=4,
    )
    gather.say(f"After the tone, please say the word {word}.")
    gather.play(audio_url(AUDIO_BEEP))

    return twiml_response(response)


@app.route("/amazon/voice-request/pin", methods=("POST",))
def amazon_voice_request_pin():
    pin = request.args["AmazonPinCode"]
    topic = request.values["Topic"]

    response = VoiceResponse()
    if not request.args.get("said_step_four"):
        response.say(f"Step {'3' if topic == 'none' else '4'}!")

    response.say(f'Your pin is {", ".join(pin)}.')
    response.pause(2)
    response.redirect(url_for("amazon_voice_request_pin", AmazonPinCode=pin, Topic=topic, said_step_four="1"))
    return twiml_response(response)
