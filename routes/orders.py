from __future__ import annotations

from datetime import datetime
from flask import Blueprint, request, session, make_response
from db import db
from helpers import error
from models import Order, OrderItem, CartItem, Product, PaymentMethod

bp = Blueprint("orders_api", __name__)

# Keep totals consistent with the cart module.
TAX_RATE = 0.13


def require_user_id():
    uid = session.get("user_id")
    if not uid:
        return None, error("unauthorized", "login required", 401)
    return uid, None


def order_to_dict(order: Order, include_items: bool = False) -> dict:
    data = {
        "id": order.id,
        "user_id": order.user_id,
        "status": order.status,
        "total_cents": getattr(order, "total_cents", None),
        "created_at": order.created_at.isoformat() if order.created_at else None,
    }
    if include_items:
        data["items"] = [
            {
                "id": oi.id,
                "product_id": oi.product_id,
                "product_name": oi.product.name if oi.product else None,
                "unit_price_cents": oi.unit_price_cents,
                "quantity": oi.quantity,
                "line_total_cents": oi.unit_price_cents * oi.quantity,
            }
            for oi in order.items
        ]
    return data


def ensure_payment_method(uid: int, payment_method_id: int | None):
    """
    Checkout must be associated with a payment method for the user.
    If caller doesn't supply payment_method_id, try default method.
    """
    if payment_method_id is not None:
        pm = PaymentMethod.query.filter_by(id=payment_method_id, user_id=uid).first()
        if not pm:
            return None, error("validation_error", "invalid payment_method_id for this user", 400)
        return pm, None

    # Try default
    pm = PaymentMethod.query.filter_by(user_id=uid, is_default=True).first()
    if pm:
        return pm, None

    # Fallback: any method
    pm = PaymentMethod.query.filter_by(user_id=uid).order_by(PaymentMethod.id.desc()).first()
    if pm:
        return pm, None

    return None, error("validation_error", "no payment methods on file", 400)


@bp.route("/orders", methods=["GET"], provide_automatic_options=False)
def list_orders():
    uid, err = require_user_id()
    if err:
        return err

    orders = (
        Order.query.filter_by(user_id=uid)
        .order_by(Order.id.desc())
        .all()
    )
    return {"items": [order_to_dict(o, include_items=False) for o in orders]}, 200


@bp.route("/orders/<int:order_id>", methods=["GET"], provide_automatic_options=False)
def get_order(order_id: int):
    uid, err = require_user_id()
    if err:
        return err

    order = Order.query.filter_by(id=order_id, user_id=uid).first()
    if not order:
        return error("not_found", "order not found", 404)

    # Ensure items relationship is loaded
    _ = order.items
    return order_to_dict(order, include_items=True), 200


@bp.route("/orders", methods=["POST"], provide_automatic_options=False)
def create_order():
    """
    Checkout:
    - requires logged-in user
    - requires payment method (explicit id OR default OR any)
    - converts user's CartItem rows -> Order + OrderItems
    - clears cart
    """
    uid, err = require_user_id()
    if err:
        return err

    payload = request.get_json(silent=True) or {}
    payment_method_id = payload.get("payment_method_id")
    if payment_method_id is not None:
        try:
            payment_method_id = int(payment_method_id)
        except Exception:
            return error("validation_error", "payment_method_id must be an integer", 400)

    pm, err = ensure_payment_method(uid, payment_method_id)
    if err:
        return err

    cart_items = CartItem.query.filter_by(user_id=uid).all()
    if not cart_items:
        return error("validation_error", "cart is empty", 400)

    # Transaction: create order, items, clear cart
    try:
        subtotal_cents = 0

        order = Order(
            user_id=uid,
            status="placed",
            created_at=datetime.utcnow(),
        )
        db.session.add(order)
        db.session.flush()  # assigns order.id

        # Bulk fetch products to avoid N+1
        product_ids = [ci.product_id for ci in cart_items]
        products = Product.query.filter(Product.id.in_(product_ids)).all()
        products_by_id = {p.id: p for p in products}

        for ci in cart_items:
            p = products_by_id.get(ci.product_id)
            if not p:
                raise ValueError(f"product not found: {ci.product_id}")

            unit_price_cents = int(p.price_cents)
            qty = int(ci.quantity)
            if qty < 1:
                raise ValueError("invalid quantity in cart")

            subtotal_cents += unit_price_cents * qty

            oi = OrderItem(
                order_id=order.id,
                product_id=p.id,
                unit_price_cents=unit_price_cents,
                quantity=qty,
            )
            db.session.add(oi)

        tax_cents = int(subtotal_cents * TAX_RATE)
        shipping_cents = 0
        total_cents = subtotal_cents + tax_cents + shipping_cents

        # If your Order model has total_cents, set it. (Some teams add it; safe-guard.)
        if hasattr(order, "total_cents"):
            order.total_cents = total_cents

        # Clear cart (single statement)
        CartItem.query.filter_by(user_id=uid).delete()

        db.session.commit()

        # Clear checkout state (server-rendered flow stores shipping + selected PM in session).
        session.pop("checkout_shipping", None)
        session.pop("checkout_payment_method_id", None)

    except ValueError as ve:
        db.session.rollback()
        return error("validation_error", str(ve), 400)
    except Exception:
        db.session.rollback()
        return error("server_error", "could not create order", 500)

    # Include items in response for order confirmation UI
    order = Order.query.filter_by(id=order.id, user_id=uid).first()
    _ = order.items
    return {
        "order": order_to_dict(order, include_items=True),
        "payment_method": {
            "id": pm.id,
            "brand": pm.brand,
            "last4": pm.last4,
            "exp_month": pm.exp_month,
            "exp_year": pm.exp_year,
        },
    }, 201


@bp.route("/orders/<int:order_id>", methods=["PATCH"], provide_automatic_options=False)
def patch_order(order_id: int):
    """
    Limited state transitions:
    - allow cancel only if status == "placed"
    """
    uid, err = require_user_id()
    if err:
        return err

    order = Order.query.filter_by(id=order_id, user_id=uid).first()
    if not order:
        return error("not_found", "order not found", 404)

    payload = request.get_json(silent=True) or {}
    new_status = payload.get("status")
    if not new_status:
        return error("validation_error", "'status' is required", 400)

    new_status = str(new_status).strip().lower()
    allowed = {"cancelled"}
    if new_status not in allowed:
        return error("validation_error", "only status='cancelled' is allowed", 400)

    if str(order.status).lower() != "placed":
        return error("validation_error", "order cannot be cancelled in its current status", 400)

    order.status = "cancelled"
    db.session.commit()

    return order_to_dict(order, include_items=False), 200


@bp.route("/orders/<int:order_id>", methods=["DELETE"], provide_automatic_options=False)
def delete_order(order_id: int):
    """
    Prefer soft-cancel: set status=cancelled.
    Do NOT hard delete by default (keeps history + helps testing evidence).
    """
    uid, err = require_user_id()
    if err:
        return err

    order = Order.query.filter_by(id=order_id, user_id=uid).first()
    if not order:
        return error("not_found", "order not found", 404)

    if str(order.status).lower() != "placed":
        return error("validation_error", "order cannot be cancelled in its current status", 400)

    order.status = "cancelled"
    db.session.commit()
    return "", 204


@bp.route("/orders", methods=["OPTIONS"])
def orders_options_collection():
    resp = make_response("", 204)
    allow = "GET,POST,OPTIONS"
    resp.headers["Allow"] = allow
    resp.headers["Access-Control-Allow-Methods"] = allow
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp

@bp.route("/orders/<int:order_id>", methods=["OPTIONS"])
def orders_options_item(order_id):
    resp = make_response("", 204)
    allow = "GET,PATCH,DELETE,OPTIONS"
    resp.headers["Allow"] = allow
    resp.headers["Access-Control-Allow-Methods"] = allow
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp