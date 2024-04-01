from pydantic.alias_generators import to_camel

from ninja import Router, Schema as BaseSchema
from ninja.errors import HttpError

from ..models import HIT, NAME_MAX_LENGTH, Assignment, Worker


router = Router()


class Schema(BaseSchema):
    class Config(BaseSchema.Config):
        alias_generator = to_camel
        populate_by_name = True


class BaseOut(Schema):
    success: bool = True


class HandshakeIn(Schema):
    assignment_id: None | str
    worker_id: None | str
    hit_id: None | str
    is_preview: bool


class HandshakeOut(BaseOut):
    topic: str
    name: str
    name_max_length: int = NAME_MAX_LENGTH
    gender: str | None = None
    is_staff: bool | None = None


class NameIn(Schema):
    name: str
    gender: str


def get_assignment(id):
    return Assignment.objects.get(hit__enabled=True, id=id)


@router.post("handshake", response=HandshakeOut, by_alias=True)
def handshake(request, handshake: HandshakeIn):
    is_staff = request.user.is_staff

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

    if handshake.is_preview:
        return {"topic": hit.topic, "is_staff": is_staff}

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
        "is_staff": is_staff,
        "name": worker.name,
        "gender": worker.gender,
    }


@router.post("name", response=BaseOut, by_alias=True)
def name(request, handshake: NameIn):
    if handshake.gender not in Worker.Gender.values:
        raise HttpError(400, f"Invalid gender {handshake.gender}")

    assignment = get_assignment(request.session["assignment_id"])
    worker = assignment.worker
    worker.name = handshake.name[:NAME_MAX_LENGTH]
    worker.gender = handshake.gender
    worker.save()
    return {"success": True}
