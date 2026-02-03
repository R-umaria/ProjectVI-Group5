from __future__ import annotations

from datetime import datetime
from flask import Blueprint, request, session

from boxedwithlove.app.extensions import db
from boxedwithlove.app.models import PaymentMethod, Order, OrderItem, Cart, CartItem, Product
from boxedwithlove.app.common.auth import login_required
from boxedwithlove.app.common.validation import get_json, require_fields
from boxedwithlove.app.common.errors import abort_json

bp = Blueprint("orders", __name__)


# --- OPTIONS (satisfies SYS-020 OPTIONS...) ---
@bp.route("/options", methods=["OPTIONS"])
def api_options():
    return ("", 204)


# --- Payment Methods ---
@bp.get("/payment-methods")
@login_required
def list_payment_methods():
    methods = PaymentMethod.query.filter_by(account_id=session["user_id"]).order_by(PaymentMethod.id.desc()).all()
    return {
        "items": [
            {
                "id": m.id,
                "brand": m.brand,
                "last4": m.last4,
                "exp_month": m.exp_month,
                "exp_year": m.exp_year,
                "billing_postal_code": m.billing_postal_code,
            }
            for m in methods
        ]
    }, 200


@bp.post("/payment-methods")
@login_required
def create_payment_method():
    data = get_json()
    require_fields(data, ["brand", "last4", "exp_month", "exp_year"])

    last4 = str(data["last4"])
    if len(last4) != 4 or not last4.isdigit():
        abort_json(400, "validation_error", "last4 must be 4 digits")

    m = PaymentMethod(
        account_id=session["user_id"],
        brand=str(data["brand"]).upper(),
        last4=last4,
        exp_month=int(data["exp_month"]),
        exp_year=int(data["exp_year"]),
        billing_postal_code=data.get("billing_postal_code"),
    )
    db.session.add(m)
    db.session.commit()
    return {"id": m.id}, 201


@bp.put("/payment-methods/<int:payment_method_id>")
@login_required
def replace_payment_method(payment_method_id: int):
    data = get_json()
    require_fields(data, ["brand", "last4", "exp_month", "exp_year"])

    m = PaymentMethod.query.filter_by(id=payment_method_id, account_id=session["user_id"]).first()
    if not m:
        abort_json(404, "not_found", "Payment method not found")

    m.brand = str(data["brand"]).upper()
    m.last4 = str(data["last4"])
    m.exp_month = int(data["exp_month"])
    m.exp_year = int(data["exp_year"])
    m.billing_postal_code = data.get("billing_postal_code")

    db.session.commit()
    return {"id": m.id}, 200


@bp.patch("/payment-methods/<int:payment_method_id>")
@login_required
def patch_payment_method(payment_method_id: int):
    data = get_json()
    m = PaymentMethod.query.filter_by(id=payment_method_id, account_id=session["user_id"]).first()
    if not m:
        abort_json(404, "not_found", "Payment method not found")

    for key in ["brand", "last4", "exp_month", "exp_year", "billing_postal_code"]:
        if key in data:
            setattr(m, key, data[key])

    if "brand" in data:
        m.brand = str(m.brand).upper()
    if "last4" in data:
        m.last4 = str(m.last4)

    db.session.commit()
    return {"id": m.id}, 200


@bp.delete("/payment-methods/<int:payment_method_id>")
@login_required
def delete_payment_method(payment_method_id: int):
    m = PaymentMethod.query.filter_by(id=payment_method_id, account_id=session["user_id"]).first()
    if not m:
        return {"message": "no_op"}, 204

    db.session.delete(m)
    db.session.commit()
    return {"message": "deleted"}, 200


# --- Orders ---
@bp.get("/orders")
@login_required
def list_orders():
    orders = Order.query.filter_by(account_id=session["user_id"]).order_by(Order.id.desc()).limit(50).all()
    return {
        "items": [
            {
                "id": o.id,
                "status": o.status,
                "total_cents": o.total_cents,
                "created_at": o.created_at.isoformat(),
            }
            for o in orders
        ]
    }, 200


@bp.get("/orders/<int:order_id>")
@login_required
def get_order(order_id: int):
    o = Order.query.filter_by(id=order_id, account_id=session["user_id"]).first()
    if not o:
        abort_json(404, "not_found", "Order not found")

    items = OrderItem.query.filter_by(order_id=o.id).all()
    return {
        "id": o.id,
        "status": o.status,
        "total_cents": o.total_cents,
        "created_at": o.created_at.isoformat(),
        "items": [
            {
                "id": i.id,
                "product_id": i.product_id,
                "quantity": i.quantity,
                "unit_price_cents": i.unit_price_cents,
            }
            for i in items
        ],
    }, 200


@bp.post("/orders")
@login_required
def create_order():
    """Checkout: cart -> order.

    Request JSON:
      {"payment_method_id": 123}
    """
    data = get_json()
    require_fields(data, ["payment_method_id"])

    payment_method_id = int(data["payment_method_id"])
    pm = PaymentMethod.query.filter_by(id=payment_method_id, account_id=session["user_id"]).first()
    if not pm:
        abort_json(400, "validation_error", "Valid payment_method_id required")

    cart = Cart.query.filter_by(account_id=session["user_id"]).first()
    if not cart:
        abort_json(409, "conflict", "Cart is empty")

    cart_items = CartItem.query.filter_by(cart_id=cart.id).all()
    if not cart_items:
        abort_json(409, "conflict", "Cart is empty")

    # Transactional order creation
    with db.session.begin():
        # Validate stock & compute totals
        total = 0
        for ci in cart_items:
            p = Product.query.get(ci.product_id)
            if not p or not p.is_active:
                abort_json(409, "conflict", "Product unavailable", {"product_id": ci.product_id})
            if p.stock_qty < ci.quantity:
                abort_json(409, "conflict", "Out of stock", {"product_id": ci.product_id, "available": p.stock_qty})

        order = Order(account_id=session["user_id"], payment_method_id=pm.id, status="PLACED", total_cents=0)
        db.session.add(order)
        db.session.flush()

        for ci in cart_items:
            p = Product.query.get(ci.product_id)
            unit = p.price_cents
            total += unit * ci.quantity

            # Decrement stock
            p.stock_qty = p.stock_qty - ci.quantity

            db.session.add(
                OrderItem(
                    order_id=order.id,
                    product_id=ci.product_id,
                    quantity=ci.quantity,
                    unit_price_cents=unit,
                )
            )

        order.total_cents = total
        order.created_at = datetime.utcnow()

        # Clear cart
        CartItem.query.filter_by(cart_id=cart.id).delete()
        cart.updated_at = datetime.utcnow()

    return {"id": order.id, "status": order.status, "total_cents": order.total_cents}, 201


@bp.patch("/orders/<int:order_id>")
@login_required
def patch_order(order_id: int):
    """Update order status (limited). Example: cancel if PLACED."""
    data = get_json()
    status = data.get("status")
    if status is None:
        abort_json(400, "validation_error", "status is required")

    o = Order.query.filter_by(id=order_id, account_id=session["user_id"]).first()
    if not o:
        abort_json(404, "not_found", "Order not found")

    # Minimal rule: can cancel only if PLACED
    if status == "CANCELLED" and o.status == "PLACED":
        o.status = "CANCELLED"
        db.session.commit()
        return {"id": o.id, "status": o.status}, 200

    abort_json(409, "conflict", "Invalid status transition")


@bp.delete("/orders/<int:order_id>")
@login_required
def delete_order(order_id: int):
    """Cancel/delete an order (recommended: soft cancel)."""
    o = Order.query.filter_by(id=order_id, account_id=session["user_id"]).first()
    if not o:
        return {"message": "no_op"}, 204

    if o.status != "PLACED":
        abort_json(409, "conflict", "Only PLACED orders can be cancelled")

    o.status = "CANCELLED"
    db.session.commit()
    return {"id": o.id, "status": o.status}, 200


@bp.route("/orders", methods=["OPTIONS"])
def orders_options():
    return ("", 204)
