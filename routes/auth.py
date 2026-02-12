from werkzeug.security import generate_password_hash, check_password_hash
from flask import Blueprint, request, session
import re

from db import db
from models import User
from helpers import error, current_user

bp = Blueprint("auth_api", __name__)

EMAIL_REGEX = r'^[^\s@]+@[^\s@]+\.[^\s@]{2,}$'


def get_password_errors(password):
    errors = []

    if len(password) < 8:
        errors.append("Password must be at least 8 characters")

    if not re.search(r"[A-Z]", password):
        errors.append("Password must include one uppercase letter")

    if not re.search(r"[a-z]", password):
        errors.append("Password must include one lowercase letter")

    if not re.search(r"[0-9]", password):
        errors.append("Password must include one number")

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("Password must include one special character")

    return errors


# Register new account
@bp.post("/users")
def register():
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    phone_number = (data.get("phone_number") or "").strip() or None

    # Required fields
    if not email or not password or not first_name or not last_name:
        return error(
            "validation_error",
            "email, password, first_name and last_name are required",
            400
        )

    # Email format check
    if not re.match(EMAIL_REGEX, email):
        return error(
            "validation_error",
            "Invalid email format",
            400
        )

    # Password strength check
    password_errors = get_password_errors(password)
    if password_errors:
        return error(
            "validation_error",
            " ".join(password_errors),
            400
        )

    # Duplicate email check
    if User.query.filter_by(email=email).first():
        return error("conflict", "email already registered", 409)

    # Create user
    user = User(
        email=email,
        password_hash=generate_password_hash(password),
        first_name=first_name,
        last_name=last_name,
        phone_number=phone_number
    )

    db.session.add(user)
    db.session.commit()

    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name
    }, 201


# POST /auth/login
@bp.post("/auth/login")
def login():
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return error("validation_error", "email and password are required", 400)

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password_hash, password):
        return error("unauthorized", "invalid credentials", 401)

    session["user_id"] = user.id

    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name
    }, 200

# POST /auth/logout
@bp.post("/auth/logout")
def logout():
    session.pop("user_id", None)
    return {"ok": True}, 200

# GET /users/me
@bp.get("/users/me")
def get_me():
    user = current_user()

    if not user:
        return error("unauthorized", "login required", 401)

    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone_number": user.phone_number
    }, 200