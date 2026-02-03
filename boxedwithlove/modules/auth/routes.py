from __future__ import annotations

from flask import Blueprint, session
from werkzeug.security import generate_password_hash, check_password_hash

from boxedwithlove.app.extensions import db
from boxedwithlove.app.models import Account, Cart
from boxedwithlove.app.common.validation import get_json, require_fields
from boxedwithlove.app.common.errors import abort_json
from boxedwithlove.app.common.auth import login_required

bp = Blueprint("auth", __name__)


@bp.post("/users")
def create_user():
    """POST /api/users - Create a new user account."""
    data = get_json()
    require_fields(data, ["email", "password", "first_name", "last_name"])

    email = data["email"].strip().lower()
    if Account.query.filter_by(email=email).first():
        abort_json(409, "conflict", "Email already registered")

    user = Account(
        email=email,
        password_hash=generate_password_hash(data["password"]),
        first_name=data["first_name"],
        last_name=data["last_name"],
        phone_number=data.get("phone_number"),
    )
    db.session.add(user)
    db.session.flush()

    # Create an empty cart for the user
    db.session.add(Cart(account_id=user.id))
    db.session.commit()

    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }, 201


@bp.post("/auth/login")
def login():
    """POST /api/auth/login - Authenticate and start a session."""
    data = get_json()
    require_fields(data, ["email", "password"])

    email = data["email"].strip().lower()
    user = Account.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, data["password"]):
        abort_json(401, "unauthorized", "Invalid email or password")

    session["user_id"] = user.id
    return {"message": "logged_in", "user_id": user.id}, 200


@bp.post("/auth/logout")
def logout():
    """POST /api/auth/logout - Terminate session."""
    session.pop("user_id", None)
    return {"message": "logged_out"}, 200


@bp.get("/users/me")
@login_required
def me():
    """GET /api/users/me - Current authenticated user."""
    user = Account.query.get(session["user_id"])
    if not user:
        abort_json(401, "unauthorized", "Invalid session")

    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone_number": user.phone_number,
    }, 200
