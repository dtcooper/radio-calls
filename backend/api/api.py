from ninja import Router, Schema, File
from ninja.errors import HttpError
from ninja.files import UploadedFile
import string
import random
import tempfile

from .models import HIT
from .utils import generate_encoded_pin, get_random_pronouncer_words, decode_speech_file
from .constants import PIN_LENGTH


def assignment_required(request):
    if "hit_id" not in request.session:
        return False

    request.hit = HIT.objects.get(id=request.session["hit_id"])
    return True


router = Router(auth=assignment_required)


class HandshakeIn(Schema):
    assignment_id: None | str
    hit_id: None | str
    worker_id: None | str

class EncodedPin(Schema):
    code: list[str]
    offsets: dict[str, list[int]]
    pin_audio_url: str

class HandshakeOut(Schema):
    topic: str
    pin: EncodedPin

class PinIn(Schema):
    pin: str

class SuccessOut(Schema):
    success: bool

class Error(Schema):
    error: str


@router.post("hit/handshake", response=HandshakeOut, auth=None)
def hit_handshake(request, handshake: HandshakeIn):
    hit = worker_id = None

    try:
        hit_qs = HIT.objects.filter(enabled=True)
        if handshake.hit_id is not None:
            hit = hit_qs.get(id=handshake.hit_id)
        elif request.user.is_authenticated:
            hit = hit_qs.latest()
    except HIT.DoesNotExist:
        pass

    if hit is None or not hit.enabled:
        raise HttpError(400, "HIT not found")

    # At least some content in worker_id
    if handshake.worker_id is not None and len(handshake.worker_id) > 6:
        worker_id = handshake.worker_id
    elif request.user.is_authenticated:
        worker_id = f"django:{request.user.id}"

    if worker_id is None:
        raise HttpError(400, "Worker ID unspecified")

    pin = "".join(random.choice(string.digits) for _ in range(PIN_LENGTH))

    request.session.update({
        "hit_id": hit.id,
        "worker_id": worker_id,
        "words": get_random_pronouncer_words(),
        "pin": pin,
        "pin_verified": False,
    })

    return {"topic": hit.topic, "pin": generate_encoded_pin(pin)}

@router.post("hit/pin", response=SuccessOut)
def hit_pin(request, pin: PinIn):
    success = pin.pin.strip() == request.session["pin"]
    if success:
        request.session["pin_verified"] = True
    return {"success": success}




@router.post("hit/audio", response=SuccessOut)
def hit_audio(request, audio: UploadedFile = File(...)):
    with tempfile.NamedTemporaryFile() as file:
        file.write(audio.read())
        file.flush()
        actual = "/".join(decode_speech_file(file.name))
        expected = "/".join(request.session["words"])
        print("  actual:", actual)
        print("expected:", expected)
        print(expected in actual)

    return {"success": True}
