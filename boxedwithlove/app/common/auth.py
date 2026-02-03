"""Very small auth layer (session-based) for the course project.

This intentionally avoids real tokens/refresh flows. We store `user_id`
into the Flask session.
"""

from functools import wraps
from typing import Callable, TypeVar, Any

from flask import session
from boxedwithlove.app.common.errors import abort_json

F = TypeVar("F", bound=Callable[..., Any])


def login_required(fn: F) -> F:
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            abort_json(401, "unauthorized", "Authentication required")
        return fn(*args, **kwargs)

    return wrapper  # type: ignore
