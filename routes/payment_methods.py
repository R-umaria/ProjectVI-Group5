from __future__ import annotations

from datetime import datetime
from flask import Blueprint, request, session, make_response
from db import db
from models import PaymentMethod
from helpers import error

bp = Blueprint("payment_methods_api", __name__)


def require_user_id():
    uid = session.get("user_id")
    if not uid:
        return None, error("unauthorized", "login required", 401)
    return uid, None


def to_dict(pm: PaymentMethod) -> dict:
    return {
        "id": pm.id,
        "cardholder_name": pm.cardholder_name,
        "brand": pm.brand,
        "last4": pm.last4,
        "exp_month": pm.exp_month,
        "exp_year": pm.exp_year,
        "billing_postal": pm.billing_postal,
        "is_default": pm.is_default,
        "created_at": pm.created_at.isoformat() if pm.created_at else None,
    }


def normalize_last4(value) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    if len(s) != 4 or not s.isdigit():
        return None
    return s


def validate_payload(data: dict, partial: bool) -> tuple[dict | None, tuple | None]:
    """
    Returns (cleaned_payload, error_response)
    partial=True for PATCH (allow missing fields)
    partial=False for POST/PUT (require all required fields)
    """
    required = ["cardholder_name", "brand", "last4", "exp_month", "exp_year"]
    cleaned: dict = {}

    def need(field: str) -> bool:
        return (not partial) or (field in data)

    # Required fields
    for f in required:
        if not partial and f not in data:
            return None, error("validation_error", f"'{f}' is required", 400)

    if need("cardholder_name"):
        v = (data.get("cardholder_name") or "").strip()
        if not v:
            return None, error("validation_error", "'cardholder_name' must be a non-empty string", 400)
        cleaned["cardholder_name"] = v

    if need("brand"):
        v = (data.get("brand") or "").strip()
        if not v:
            return None, error("validation_error", "'brand' must be a non-empty string", 400)
        cleaned["brand"] = v

    if need("last4"):
        v = normalize_last4(data.get("last4"))
        if not v:
            return None, error("validation_error", "'last4' must be exactly 4 digits", 400)
        cleaned["last4"] = v

    if need("exp_month"):
        try:
            v = int(data.get("exp_month"))
        except Exception:
            return None, error("validation_error", "'exp_month' must be an integer 1-12", 400)
        if v < 1 or v > 12:
            return None, error("validation_error", "'exp_month' must be between 1 and 12", 400)
        cleaned["exp_month"] = v

    if need("exp_year"):
        try:
            v = int(data.get("exp_year"))
        except Exception:
            return None, error("validation_error", "'exp_year' must be an integer year", 400)
        # keep validation simple but sane
        year_now = datetime.utcnow().year
        if v < year_now - 1 or v > year_now + 25:
            return None, error("validation_error", "'exp_year' is out of allowed range", 400)
        cleaned["exp_year"] = v

    # Optional fields
    if "billing_postal" in data:
        bp = data.get("billing_postal")
        cleaned["billing_postal"] = (str(bp).strip() if bp is not None else None)

    if "is_default" in data:
        cleaned["is_default"] = bool(data.get("is_default"))

    return cleaned, None


def apply_default_rule(uid: int, pm: PaymentMethod, want_default: bool):
    """
    If want_default=True -> unset other defaults for this user then set this one.
    """
    if not want_default:
        return
    PaymentMethod.query.filter(
        PaymentMethod.user_id == uid,
        PaymentMethod.id != pm.id,
        PaymentMethod.is_default.is_(True),
    ).update({"is_default": False})
    pm.is_default = True


@bp.route("/payment-methods", methods=["GET"], provide_automatic_options=False)
def list_payment_methods():
    uid, err = require_user_id()
    if err:
        return err

    items = (
        PaymentMethod.query.filter_by(user_id=uid)
        .order_by(PaymentMethod.is_default.desc(), PaymentMethod.id.desc())
        .all()
    )
    return {"items": [to_dict(pm) for pm in items]}, 200


@bp.route("/payment-methods", methods=["POST"], provide_automatic_options=False)
def create_payment_method():
    uid, err = require_user_id()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    cleaned, err = validate_payload(data, partial=False)
    if err:
        return err

    pm = PaymentMethod(user_id=uid, **cleaned)
    db.session.add(pm)
    db.session.flush()  # assign id

    # If first payment method, force default. Otherwise respect is_default flag.
    count_for_user = PaymentMethod.query.filter_by(user_id=uid).count()
    if count_for_user == 1:
        apply_default_rule(uid, pm, True)
    else:
        apply_default_rule(uid, pm, bool(cleaned.get("is_default", False)))

    db.session.commit()
    return to_dict(pm), 201


@bp.route("/payment-methods/<int:payment_method_id>", methods=["PUT"], provide_automatic_options=False)
def replace_payment_method(payment_method_id: int):
    uid, err = require_user_id()
    if err:
        return err

    pm = PaymentMethod.query.filter_by(id=payment_method_id, user_id=uid).first()
    if not pm:
        return error("not_found", "payment method not found", 404)

    data = request.get_json(silent=True) or {}
    cleaned, err = validate_payload(data, partial=False)
    if err:
        return err

    for k, v in cleaned.items():
        setattr(pm, k, v)

    apply_default_rule(uid, pm, bool(cleaned.get("is_default", pm.is_default)))
    db.session.commit()
    return to_dict(pm), 200


@bp.route("/payment-methods/<int:payment_method_id>", methods=["PATCH"], provide_automatic_options=False)
def update_payment_method(payment_method_id: int):
    uid, err = require_user_id()
    if err:
        return err

    pm = PaymentMethod.query.filter_by(id=payment_method_id, user_id=uid).first()
    if not pm:
        return error("not_found", "payment method not found", 404)

    data = request.get_json(silent=True) or {}
    cleaned, err = validate_payload(data, partial=True)
    if err:
        return err

    for k, v in cleaned.items():
        setattr(pm, k, v)

    if "is_default" in cleaned:
        apply_default_rule(uid, pm, bool(cleaned["is_default"]))

    db.session.commit()
    return to_dict(pm), 200


@bp.route("/payment-methods/<int:payment_method_id>", methods=["DELETE"], provide_automatic_options=False)
def delete_payment_method(payment_method_id: int):
    uid, err = require_user_id()
    if err:
        return err

    pm = PaymentMethod.query.filter_by(id=payment_method_id, user_id=uid).first()
    if not pm:
        return error("not_found", "payment method not found", 404)

    was_default = bool(pm.is_default)
    db.session.delete(pm)
    db.session.flush()

    # If deleting the default, promote another one (if any) to default.
    if was_default:
        next_pm = (
            PaymentMethod.query.filter_by(user_id=uid)
            .order_by(PaymentMethod.id.desc())
            .first()
        )
        if next_pm:
            apply_default_rule(uid, next_pm, True)

    db.session.commit()
    return "", 204


# Optional: explicit OPTIONS for these resources (already have /api/options, but this is cleaner)
from flask import make_response

@bp.route("/payment-methods", methods=["OPTIONS"])
def payment_methods_options_collection():
    resp = make_response("", 204)
    allow = "GET,POST,OPTIONS"
    resp.headers["Allow"] = allow
    resp.headers["Access-Control-Allow-Methods"] = allow
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp

@bp.route("/payment-methods/<int:payment_method_id>", methods=["OPTIONS"])
def payment_methods_options_item(payment_method_id):
    resp = make_response("", 204)
    allow = "GET,PUT,PATCH,DELETE,OPTIONS"
    resp.headers["Allow"] = allow
    resp.headers["Access-Control-Allow-Methods"] = allow
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp
