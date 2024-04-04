import datetime
import logging
import uuid

from pydantic.alias_generators import to_camel
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant

from django.conf import settings
from django.http import Http404

from ninja import NinjaAPI, Schema as BaseSchema
from ninja.errors import AuthenticationError, HttpError, ValidationError

from ..constants import ESTIMATED_BEFORE_VERIFIED_DURATION
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
    is_prod: bool = False
    estimated_before_verified_duration: datetime.timedelta = ESTIMATED_BEFORE_VERIFIED_DURATION
    min_call_duration: datetime.timedelta
    leave_voicemail_after_duration: datetime.timedelta


class HandshakeOut(HandshakePreviewOut):
    assignment_id: str
    gender: str
    hit_id: str | None
    name_max_length: int = WORKER_NAME_MAX_LENGTH
    name: str
    token: str
    worker_id: str
    location: str


class BaseIn(Schema):
    assignment_id: str


class NameIn(BaseIn):
    name: str
    gender: str


class TokenOut(BaseOut):
    token: str


class FinalizeOut(BaseOut):
    accepted: bool
    approval_code: uuid.UUID | None = None


def get_token(worker):
    token = AccessToken(
        settings.TWILIO_ACCOUNT_SID, settings.TWILIO_API_KEY, settings.TWILIO_API_SECRET, identity=worker.id
    )
    grant = VoiceGrant(outgoing_application_sid=settings.TWILIO_TWIML_APP_SID)
    token.add_grant(grant)
    return token.to_jwt()


def get_hit_and_common_handshake_out(request, handshake):
    hit = None
    try:
        if handshake.hit_id is not None:
            hit = HIT.objects.get(amazon_id=handshake.hit_id)
        elif request.user.has_perm("api.preview_hit"):
            if handshake.db_id is not None:
                hit = HIT.objects.get(id=handshake.db_id)
            else:
                hit = HIT.objects.latest()
    except HIT.DoesNotExist:
        pass

    if hit is None:
        raise HttpError(400, "HIT not found!")

    handshake_out = {
        "topic": hit.topic,
        "show_host": hit.show_host,
        "is_staff": request.user.is_staff,
        "is_prod": not settings.DEBUG,
        "min_call_duration": hit.min_call_duration,
        "leave_voicemail_after_duration": hit.leave_voicemail_after_duration,
    }
    return hit, handshake_out


def get_assignment(amazon_id) -> Assignment:
    return Assignment.objects.get(amazon_id=amazon_id)


@api.post("handshake/preview", response=HandshakePreviewOut, by_alias=True)
def handshake_preview(request, handshake: HandshakeIn):
    _, handshake_out = get_hit_and_common_handshake_out(request, handshake)
    return handshake_out


@api.post("handshake", response=HandshakeOut, by_alias=True)
def handshake(request, handshake: HandshakeIn):
    hit, handshake_out = get_hit_and_common_handshake_out(request, handshake)
    is_staff = request.user.is_staff

    worker_id = None
    simulated_worker = False
    if handshake.worker_id is not None:
        worker_id = handshake.worker_id
    elif is_staff:
        worker_id = f"simulated/user:{request.user.id}"
    if worker_id is None:
        raise HttpError(400, "Worker ID invalid")

    worker = Worker.from_api(request, worker_id)

    assignment_id = None
    if handshake.assignment_id is not None:
        assignment_id = handshake.assignment_id
    elif is_staff:
        assignment_id = f"simulated/user:{request.user.id}/worker:{worker.id}/hit:{hit.id}"
        simulated_worker = True
    if assignment_id is None:
        raise HttpError(400, "Assignment ID invalid")

    # Reset to initial state for simulated workers only
    assignment = Assignment.from_api(amazon_id=assignment_id, hit=hit, worker=worker, reset_to_initial=simulated_worker)

    return {
        **handshake_out,
        "assignment_id": assignment.amazon_id,
        "gender": worker.gender,
        "hit_id": hit.amazon_id,
        "name": worker.name,
        "token": get_token(worker),
        "worker_id": worker.amazon_id,
        "location": worker.location,
    }


@api.post("token", response=TokenOut, by_alias=True)
def token(request, token: BaseIn):
    assignment = get_assignment(amazon_id=token.assignment_id)
    return {"token": get_token(assignment.worker)}


@api.post("name", response=BaseOut, by_alias=True)
def name(request, name: NameIn):
    assignment = get_assignment(amazon_id=name.assignment_id)

    if name.gender not in Worker.Gender.values:
        raise HttpError(400, f"Invalid gender {name.gender}")

    new_name = name.name.strip()[:WORKER_NAME_MAX_LENGTH]
    if not new_name:
        raise HttpError(400, "Empty name!")

    worker = assignment.worker
    worker.name = new_name
    worker.gender = name.gender
    worker.save()
    return {"success": True}


@api.post("finalize", response=FinalizeOut, by_alias=True)
def finalize(request, finalize: BaseIn):
    # This could happen during voicemail callback, so wrap it in a transaction
    assignment = get_assignment(amazon_id=finalize.assignment_id)

    # Same as in frontend, if we got here it may be beacuse a call got disconnected abruptly
    # so a request to finalize should be accepted anyway
    if assignment.stage in (Assignment.Stage.VOICEMAIL, Assignment.Stage.CALL):
        assignment.stage = Assignment.Stage.DONE
        assignment.save()

    if assignment.stage == Assignment.Stage.DONE:
        return {"accepted": True, "approval_code": assignment.hit.approval_code}
    else:
        return {"accepted": False}
