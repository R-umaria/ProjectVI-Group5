import uuid
from flask import g, request

REQUEST_ID_HEADER = "X-Request-ID"


def init_request_id() -> str:
    rid = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
    g.request_id = rid
    return rid
