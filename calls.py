import random
import re
from urllib.parse import unquote, urlencode

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client as TwilioClient
from twilio.twiml.messaging_response import MessagingResponse
from twilio.twiml.voice_response import VoiceResponse

from flask import Flask, Response, jsonify, request, render_template, url_for

app = Flask(__name__)
if app.env == 'development':
    import json
    import pprint
    import xml.dom.minidom

    from werkzeug.middleware.proxy_fix import ProxyFix

    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)

    @app.after_request
    def log_request(response):
        print(' Headers '.center(40, '='))
        pprint.pprint(dict(request.headers))

        if request.method == 'POST':
            print(' POST '.center(40, '='))
            pprint.pprint(dict(request.form))

        content_type = response.headers.get('Content-Type')

        if content_type == 'text/xml':
            print(' TwiML '.center(40, '='))
            dom = xml.dom.minidom.parseString(response.data)
            print(dom.toprettyxml())
        elif content_type == 'application/json':
            print(' JSON '.center(40, '='))
            print(json.dumps(json.loads(response.data), indent=2, sort_keys=True))

        return response

else:
    import logging

    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

# sip password = ***REMOVED***
TWILIO_ACCOUNT_SID = '***REMOVED***'
TWILIO_AUTH_TOKEN = '***REMOVED***'
DEFAULT_AREA_CODE = '***REMOVED***'
SMS_ADMIN_NUMBER = '***REMOVED***'
NUMBERS_TO_SIP_ADDRESSES = {'***REMOVED***': 'tigwit', '***REMOVED***': 'poolabs'}
SIP_DOMAIN = '***REMOVED***'
VOICEMAIL_EMAIL = '***REMOVED***'

AUDIO_VOICEMAIL_TO_NUMBERS = {'***REMOVED***': 'voicemail', '***REMOVED***': 'poolabs-voicemail'}
AUDIO_HOLD_MUSIC_LIST = ('hold-music-1', 'hold-music-2', 'hold-music-3')
AUDIO_COMPLETED_MUSIC = 'completed-music'
AUDIO_NOT_IN_SERVICE = 'not-in-service'

SIP_ADDRESSES_TO_NUMBERS = {v: k for k, v in NUMBERS_TO_SIP_ADDRESSES.items()}


twilio_client = client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def twiml_response(response):
    return Response(str(response), content_type='text/xml')


def sanitize_phone_number(phone_number):
    if phone_number:
        if len(phone_number) == 7 and phone_number.isdigit():
            phone_number = f'{DEFAULT_AREA_CODE}{phone_number}'

        # Replace double zero with plus, because I'm used to that shit!
        for intl_prefix in ('00', '011'):
            if phone_number.startswith(intl_prefix):
                phone_number = '+' + phone_number[len(intl_prefix):]

        try:
            lookup = twilio_client.lookups.phone_numbers(phone_number).fetch(country_code='US')
        except TwilioRestException:
            pass
        else:
            return lookup.phone_number


def parse_sip_address(address):
    if isinstance(address, str):
        match = re.search(r'^sip:([^@]+)@', address)
        if match:
            return unquote(match.group(1))

    return None


def audio_url(filename, external=False):
    return url_for('static', filename=f'audio/{filename}.mp3', _external=external)


@app.route('/sip-outgoing', methods=('POST',))
def sip_outgoing():
    response = VoiceResponse()

    from_sip = parse_sip_address(request.form['From'])
    from_number = SIP_ADDRESSES_TO_NUMBERS.get(from_sip)
    if from_number:
        to_number = sanitize_phone_number(parse_sip_address(request.form['To']))
        if to_number:
            response.dial(to_number, answer_on_bridge=True, caller_id=from_number)

        else:
            response.play(audio_url(AUDIO_NOT_IN_SERVICE))
    else:
        response.say('Error. No number for SIP address.')

    return twiml_response(response)


@app.route('/voice-incoming', methods=('POST',))
def voice_incoming():
    response = VoiceResponse()

    from_number = sanitize_phone_number(request.form['From'])
    to_number = request.form['To']

    if request.args.get('from_amazon'):
        from_number, to_number = to_number, from_number

    to_sip = NUMBERS_TO_SIP_ADDRESSES.get(to_number)

    if to_sip:
        to_sip = f'{to_sip}@{SIP_DOMAIN}'
        dial = response.dial(answer_on_bridge=True, action='/voice-incoming/done', caller_id=from_number)
        dial.sip(to_sip)
    else:
        response.say('Error. No SIP address for number.')

    return twiml_response(response)


@app.route('/voice-incoming/done', methods=('POST',))
def voice_incoming_done():
    response = VoiceResponse()
    to_number = request.form['To']
    status = request.form.get('DialCallStatus')
    sip_code = request.form.get('DialSipResponseCode')

    if status == 'completed':
        response.play(audio_url(AUDIO_COMPLETED_MUSIC))
    elif status == 'busy' and sip_code == '486':  # 486 = Busy Here
        response.play(audio_url(random.choice(AUDIO_HOLD_MUSIC_LIST)))
        response.redirect(url_for('voice_incoming'))
    else:
        audio = AUDIO_VOICEMAIL_TO_NUMBERS.get(to_number)
        message = audio_url(audio, external=True) if audio else 'Please leave a message after the tone.'
        response.redirect('http://twimlets.com/voicemail?' + urlencode(
            {'Email': VOICEMAIL_EMAIL, 'Message': message, 'Transcribe': 'True'}))

    return twiml_response(response)


@app.route('/sms', methods=('POST',))
def sms():
    from_number = request.form['From']
    to_number = request.form['To']
    body = request.form['Body']

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
            response.message(f'Sent to {recipient_number} - {body}')
        else:
            response.message('No recipient found! Message not sent.')

        return twiml_response(response)

    else:
        client.messages.create(to=SMS_ADMIN_NUMBER, from_=to_number, body=f"From {from_number} - {body}")
        return Response(status=204)


@app.route('/amazon-call/ajax/initiate', methods=('POST',))
def amazon_call_ajax_initiate():
    to_number = sanitize_phone_number(''.join(filter(str.isdigit, request.form['number'])))
    from_number = SIP_ADDRESSES_TO_NUMBERS.get(request.form['show'])

    if to_number:
        code = str(random.randint(0, 9999)).zfill(4)

        call = twilio_client.calls.create(
            url=url_for('amazon_call_initiate', code=code, _external=True, _scheme='https'),
            to=to_number,
            from_=from_number,
        )

        data = {'success': True, 'code': code, 'call_sid': call.sid}
    else:
        data = {'success': False, 'error': 'Invalid phone number. Try again.'}

    response = jsonify(data)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route('/amazon-call/ajax/confirm', methods=('POST',))
def amazon_call_ajax_confirm():
    call_sid = request.form['call_sid']

    try:
        call = client.calls(call_sid).update(
            method='POST',
            url=url_for('voice_incoming', from_amazon='1', _external=True, _scheme='https'),
        )
        data = {'success': True}
    except TwilioRestException:
        data = {'success': False, 'error': 'Did you hang up? Error. Please try again.'}

    response = jsonify(data)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route('/amazon-call/initiate/<code>', methods=('POST',))
def amazon_call_initiate(code):
    response = VoiceResponse()
    response.say(f'The pin code is {", ".join(code)}. Enter the pin code and do not hang up.')
    response.pause(1)
    response.redirect(url_for('amazon_call_initiate', code=code))
    return twiml_response(response)


@app.route('/')
def index():
    return Response('There are forty people in the world and five of them are hamburgers.', content_type='text/plain')
