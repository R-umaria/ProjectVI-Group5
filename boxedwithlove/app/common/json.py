from __future__ import annotations

from flask import jsonify

def ok(data=None, status=200):
    if data is None:
        return ("", status)
    return jsonify(data), status
