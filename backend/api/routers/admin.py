import datetime
import uuid

from django.conf import settings

from ninja import Router

from ..models import HIT
from .common import BaseOut, Schema


def staff_only(request):
    return request.user.is_staff


router = Router(auth=staff_only)


class HITOut(Schema):
    id: str
    topic: str
    peer_id: uuid.UUID
    location: str
    created_at: datetime.datetime


class HandshakeOut(BaseOut):
    success: bool = True
    peerjs_key: str = settings.PEERJS_KEY
    hits: list[HITOut]


@router.post("handshake", response=HandshakeOut, by_alias=True)
def handshake(request):
    return {"hits": [hit.serialize() for hit in HIT.objects.filter(enabled=True)]}
