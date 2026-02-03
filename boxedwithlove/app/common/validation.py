from __future__ import annotations

from typing import Any, Dict, Iterable
from flask import request

from boxedwithlove.app.common.errors import abort_json


def get_json() -> Dict[str, Any]:
    if not request.is_json:
        abort_json(400, "invalid_json", "Request must be application/json")
    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        abort_json(400, "invalid_json", "Malformed JSON body")
    return data


def require_fields(data: Dict[str, Any], fields: Iterable[str]) -> None:
    missing = [f for f in fields if f not in data]
    if missing:
        abort_json(400, "validation_error", "Missing required fields", {"missing": missing})
