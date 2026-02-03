from werkzeug.security import generate_password_hash, check_password_hash
from flask import Blueprint, request, session

from db import db
from models import User
from app import error  # uses the shared error() function

bp = Blueprint("auth_api", __name__)

@bp.post("/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or not password:
        return error("validation_error", "email and password are required", 400)

    if User.query.filter_by(email=email).first():
        return error("conflict", "email already registered", 409)

    user = User(email=email, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()

    session["user_id"] = user.id
    return {"id": user.id, "email": user.email}, 201

@bp.post("/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return error("unauthorized", "invalid credentials", 401)

    session["user_id"] = user.id
    return {"id": user.id, "email": user.email}, 200

@bp.post("/auth/logout")
def logout():
    session.pop("user_id", None)
    return {"ok": True}, 200
