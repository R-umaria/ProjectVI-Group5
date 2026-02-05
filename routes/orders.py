from flask import Blueprint, request, session
from db import db
from models import CartItem, Order, OrderItem
from helpers import error, current_user
bp = Blueprint("orders_api", __name__)

def require_user_id():
    uid = session.get("user_id")
    if not uid:
        return None, error("unauthorized", "login required", 401)
    return uid, None

@bp.get("/orders")
def list_orders():
    uid, err = require_user_id()
    if err:
        return err
    orders = Order.query.filter_by(user_id=uid).order_by(Order.id.desc()).limit(50).all()
    return {
        "items": [
            {"id": o.id, "total_cents": o.total_cents, "status": o.status, "created_at": o.created_at.isoformat()}
            for o in orders
        ]
    }, 200

@bp.post("/orders")
def checkout():
    uid, err = require_user_id()
    if err:
        return err

    # Minimal checkout: uses current cart to create an order.
    cart_items = CartItem.query.filter_by(user_id=uid).all()
    if not cart_items:
        return error("validation_error", "cart is empty", 400)

    try:
        # transaction
        total = sum(i.product.price_cents * i.quantity for i in cart_items)
        order = Order(user_id=uid, total_cents=total, status="placed")
        db.session.add(order)
        db.session.flush()  # get order.id

        for i in cart_items:
            db.session.add(OrderItem(
                order_id=order.id,
                product_id=i.product_id,
                unit_price_cents=i.product.price_cents,
                quantity=i.quantity
            ))
            db.session.delete(i)

        db.session.commit()
        return {"id": order.id, "total_cents": order.total_cents, "status": order.status}, 201
    except Exception:
        db.session.rollback()
        return error("server_error", "checkout failed", 500)
