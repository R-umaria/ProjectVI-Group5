from flask import jsonify, session, g
from models import User

def error(code: str, message: str, status: int = 400, details: dict | None = None):
    payload = {"error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    return jsonify(payload), status

def current_user() -> User | None:
    if "current_user" not in g:
        uid = session.get("user_id")
        g.current_user = User.query.get(uid) if uid else None
    return g.current_user