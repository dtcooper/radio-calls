import logging

from pydantic.alias_generators import to_camel
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant

from django.conf import settings
from django.http import Http404

from ninja import NinjaAPI, Schema as BaseSchema
from ninja.errors import AuthenticationError, HttpError, ValidationError

from ..models import HIT, WORKER_NAME_MAX_LENGTH, Assignment, Worker


api = NinjaAPI(urls_namespace="hit")


logger = logging.getLogger("django")


def register_exec_handler(exception, code, message):
    @api.exception_handler(exception)
    def _(request, exc):
        logger.exception(exc)
        return api.create_response(request, {"success": False, "error": message}, status=code)


for exception, code, message in (
    (Exception, 500, "Unexpected error ocurred!"),
    (AuthenticationError, 401, "Access denied!"),
    (ValidationError, 422, "Client exchanged data with server in an unexpected or bad way"),
    (Http404, 404, "Something you're looking for was not found"),
):
    register_exec_handler(exception, code, message)


@api.exception_handler(HttpError)
def http_error_handler(request, exc):
    logger.exception(exc)
    return api.create_response(request, {"success": False, "error": exc.message}, status=exc.status_code)


class Schema(BaseSchema):
    class Config(BaseSchema.Config):
        alias_generator = to_camel
        populate_by_name = True


class BaseOut(Schema):
    success: bool = True


class HandshakeIn(Schema):
    assignment_id: str | None = None
    db_id: int | None = None
    worker_id: str | None = None
    hit_id: str | None = None
    is_preview: bool = False


class HandshakePreviewOut(BaseOut):
    topic: str
    show_host: str
    is_staff: bool


class HandshakeOut(HandshakePreviewOut):
    assignment_id: str
    gender: str
    hit_id: str | None
    name_max_length: int = WORKER_NAME_MAX_LENGTH
    name: str
    token: str
    worker_id: str
    submit_url: str | None


class NameIn(Schema):
    name: str
    gender: str


class TokenOut(BaseOut):
    token: str


def get_assignment_from_session(request):
    return Assignment.objects.get(id=request.session["assignment_id"])


def get_hit_from_handshake(request, handshake):
    hit = None
    try:
        if handshake.hit_id is not None:
            hit = HIT.objects.get(amazon_id=handshake.hit_id)
        elif request.user.is_staff:
            if handshake.db_id is not None:
                hit = HIT.objects.get(id=handshake.db_id)
            else:
                hit = HIT.objects.latest()
    except HIT.DoesNotExist:
        pass

    if hit is None:
        raise HttpError(400, "HIT not found!")

    return hit


def get_token(worker):
    token = AccessToken(
        settings.TWILIO_ACCOUNT_SID, settings.TWILIO_API_KEY, settings.TWILIO_API_SECRET, identity=worker.id
    )
    grant = VoiceGrant(outgoing_application_sid=settings.TWILIO_TWIML_APP_SID)
    token.add_grant(grant)
    return token.to_jwt()


@api.post("handshake/preview", response=HandshakePreviewOut, by_alias=True)
def handshake_preview(request, handshake: HandshakeIn):
    hit = get_hit_from_handshake(request, handshake)
    return {"topic": hit.topic, "is_staff": request.user.is_staff, "show_host": hit.show_host}


@api.post("handshake", response=HandshakeOut, by_alias=True)
def handshake(request, handshake: HandshakeIn):
    hit = get_hit_from_handshake(request, handshake)
    is_staff = request.user.is_staff

    worker_id = None
    if handshake.worker_id is not None:
        worker_id = handshake.worker_id
    elif is_staff:
        worker_id = f"django:{request.user.id}"
    if worker_id is None:
        raise HttpError(400, "Worker ID invalid")

    worker = Worker.from_api(worker_id)

    assignment_id = None
    if handshake.assignment_id is not None:
        assignment_id = handshake.assignment_id
    elif is_staff:
        assignment_id = f"{worker.id}:{hit.id}"
    if assignment_id is None:
        raise HttpError(400, "Assignment ID invalid")

    assignment = Assignment.from_api(assignment_id, hit=hit, worker=worker)
    request.session.update({"assignment_id": assignment.id})

    submit_url = None
    if hit.status == HIT.Status.SANDBOX:
        submit_url = "https://workersandbox.mturk.com/mturk/externalSubmit"
    elif hit.status == HIT.Status.PRODUCTION:
        submit_url = "https://www.mturk.com/mturk/externalSubmit"

    return {
        "assignment_id": assignment.amazon_id,
        "gender": worker.gender,
        "hit_id": hit.amazon_id,
        "is_staff": is_staff,
        "name": worker.name,
        "token": get_token(worker),
        "show_host": hit.show_host,
        "topic": hit.topic,
        "worker_id": worker.amazon_id,
        "submit_url": submit_url,
    }


@api.post("token", response=TokenOut, by_alias=True)
def token(request):
    assignment = get_assignment_from_session(request)
    return {"token": get_token(assignment.worker)}


@api.post("name", response=BaseOut, by_alias=True)
def name(request, name: NameIn):
    if name.gender not in Worker.Gender.values:
        raise HttpError(400, f"Invalid gender {name.gender}")

    assignment = get_assignment_from_session(request)
    worker = assignment.worker
    worker.name = name.name[:WORKER_NAME_MAX_LENGTH]
    worker.gender = name.gender
    worker.save()
    return {"success": True}
