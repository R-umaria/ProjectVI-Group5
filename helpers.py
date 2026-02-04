from flask import jsonify, session
from models import User

def error(code: str, message: str, status: int = 400, details: dict | None = None):
    payload = {"error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    return jsonify(payload), status

def current_user() -> User | None:
    uid = session.get("user_id")
    if not uid:
        return None
    return User.query.get(uid)