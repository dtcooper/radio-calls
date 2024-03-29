import uuid

from django.templatetags.static import static

from ninja import File, Router
from ninja.errors import HttpError
from ninja.files import UploadedFile

from ..constants import PRONOUNCER_WORDS
from ..models import HIT, Assignment, Worker
from .common import Schema


def assignment_required_in_session(request):
    assignment_id = request.session.get("assignment_id")
    if assignment_id is None:
        return False

    request.assignment = Assignment.objects.filter(hit__enabled=True).get(id=assignment_id)
    return True


router = Router(auth=assignment_required_in_session)


class BaseOut(Schema):
    success: bool = True


class TopicOnlyHandshakeIn(Schema):
    hit_id: None | str


class HandshakeIn(TopicOnlyHandshakeIn):
    assignment_id: None | str
    worker_id: None | str


class Pronouncer(Schema):
    words: list[str]
    word_list: dict[str, dict[str, float]] = PRONOUNCER_WORDS
    audio_url: str = static("api/hit/pronouncer.mp3")


class TopicOnlyHandshakeOut(BaseOut):
    topic: str
    is_staff: bool


class HandshakeOut(TopicOnlyHandshakeOut):
    peer_id: uuid.UUID
    pronouncer: Pronouncer


class PronouncerOut(BaseOut):
    verified: bool
    remote_peer_id: None | uuid.UUID
    heard_words: list[str]


def get_hit(request, handshake: TopicOnlyHandshakeIn | HandshakeIn):
    hit = None
    try:
        hit_qs = HIT.objects.filter(enabled=True)
        if handshake.hit_id is not None:
            hit = hit_qs.get(id=handshake.hit_id)
        elif request.user.is_staff:
            hit = hit_qs.latest()
    except HIT.DoesNotExist:
        pass

    if hit is None:
        raise HttpError(400, "HIT not found!")

    return hit


@router.post("handshake/topic", response=TopicOnlyHandshakeOut, auth=None, by_alias=True)
def handshake_topic(request, handshake: TopicOnlyHandshakeIn):
    return {"topic": get_hit(request, handshake).topic, "is_staff": request.user.is_staff}


@router.post("handshake", response=HandshakeOut, auth=None, by_alias=True)
def handshake(request, handshake: HandshakeIn):
    hit = get_hit(request, handshake)
    is_staff = request.user.is_staff

    worker_id = None
    if handshake.worker_id is not None and len(handshake.worker_id) > 10:
        worker_id = handshake.worker_id
    elif is_staff:
        worker_id = f"django:{request.user.id}"
    if worker_id is None:
        raise HttpError(400, "Worker ID invalid")

    worker, _ = Worker.objects.get_or_create(id=worker_id)

    assignment_id = None
    if handshake.assignment_id is not None and len(handshake.assignment_id) > 10:
        assignment_id = handshake.assignment_id
    elif is_staff:
        assignment_id = f"{worker.id}:{hit.id}"
    if assignment_id is None:
        raise HttpError(400, "Assignment ID invalid")

    assignment = Assignment.from_api(assignment_id, hit=hit, worker=worker)
    request.session.update({"assignment_id": assignment.id})

    return {
        "topic": hit.topic,
        "pronouncer": {"words": assignment.pronouncer},
        "is_staff": is_staff,
        "peer_id": worker.peer_id,
    }


@router.post("verify", response=PronouncerOut, by_alias=True)
def pronouncer(request, audio: UploadedFile = File(...)):
    assignment: Assignment = request.assignment
    success, heard_words = assignment.match_pronouncer_from_audio_file(audio.file.name)

    peer_id = None
    if success:
        assignment.stage = max(Assignment.Stage.VERIFIED, assignment.stage)
        assignment.save()
        peer_id = assignment.hit.peer_id

    return {"verified": success, "remote_peer_id": peer_id, "heard_words": heard_words}
