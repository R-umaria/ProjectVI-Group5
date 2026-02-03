import uuid
from flask import g, request

REQUEST_ID_HEADER = "X-Request-Id"


def assign_request_id():
    """Attach a request id to `g` and mirror it in the response header."""
    incoming = request.headers.get(REQUEST_ID_HEADER)
    g.request_id = incoming or str(uuid.uuid4())
