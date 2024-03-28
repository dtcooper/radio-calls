import tempfile

from pydantic.alias_generators import to_camel

from django.templatetags.static import static

from ninja import File, Router, Schema as _Schema
from ninja.errors import HttpError
from ninja.files import UploadedFile

from .models import HIT
from .utils import encode_pin, generate_pin, generate_pronouncer, match_pronouncer_from_audio_file


def assignment_required(request):
    if "hit_id" not in request.session:
        return False

    request.hit = HIT.objects.get(id=request.session["hit_id"], enabled=True)
    return True


router = Router(auth=assignment_required)


class Schema(_Schema):
    class Config(_Schema.Config):
        alias_generator = to_camel
        populate_by_name = True


class BaseOut(Schema):
    success: bool = True


class HandshakeIn(Schema):
    assignment_id: None | str
    hit_id: None | str
    worker_id: None | str


class EncodedPin(Schema):
    code: list[str]
    offsets: dict[str, list[int]]
    audio_url: str


class HandshakeOut(BaseOut):
    topic: str
    pin: EncodedPin
    pronouncer: list[str]


class PinIn(Schema):
    pin: str


class AcceptedOut(BaseOut):
    accepted: bool


class Error(Schema):
    error: str


@router.post("hit/handshake", response=HandshakeOut, auth=None, by_alias=True)
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
        raise HttpError(400, "Worker ID invalid")

    pin = generate_pin()
    pronouncer = generate_pronouncer()

    request.session.update({
        "hit_id": hit.id,
        "worker_id": worker_id,
        "pronouncer": pronouncer,
        "pronouncer_verified": False,
        "pin": pin,
        "pin_verified": False,
    })

    return {
        "topic": hit.topic,
        "pin": {**encode_pin(pin), "audio_url": static("api/hit/numbers.mp3")},
        "pronouncer": pronouncer,
    }


@router.post("hit/verify/pin", response=AcceptedOut, by_alias=True)
def hit_pin(request, pin: PinIn):
    success = pin.pin.strip() == request.session["pin"]
    if success:
        request.session["pin_verified"] = True
    print(dict(request.session))
    return {"accepted": success}


@router.post("hit/verify/pronouncer", response=AcceptedOut, by_alias=True)
def hit_pronouncer(request, audio: UploadedFile = File(...)):
    with tempfile.NamedTemporaryFile(delete_on_close=False) as file:
        file.write(audio.read())
        file.close()
        success = match_pronouncer_from_audio_file(file.name, request.session["pronouncer"])

    if success:
        request.session["pronouncer_verified"] = True

    return {"accepted": success}
