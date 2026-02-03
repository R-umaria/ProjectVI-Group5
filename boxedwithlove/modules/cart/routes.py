from __future__ import annotations

from datetime import datetime
from flask import Blueprint, session

from boxedwithlove.app.extensions import db
from boxedwithlove.app.models import Cart, CartItem, Product
from boxedwithlove.app.common.auth import login_required
from boxedwithlove.app.common.validation import get_json, require_fields
from boxedwithlove.app.common.errors import abort_json

bp = Blueprint("cart", __name__)


def _get_cart() -> Cart:
    cart = Cart.query.filter_by(account_id=session["user_id"]).first()
    if not cart:
        cart = Cart(account_id=session["user_id"])  # safety
        db.session.add(cart)
        db.session.commit()
    return cart


def _cart_response(cart: Cart):
    items = (
        CartItem.query.filter_by(cart_id=cart.id)
        .all()
    )
    total = sum(i.quantity * i.unit_price_cents for i in items)
    return {
        "cart_id": cart.id,
        "items": [
            {
                "id": i.id,
                "product_id": i.product_id,
                "quantity": i.quantity,
                "unit_price_cents": i.unit_price_cents,
                "line_total_cents": i.quantity * i.unit_price_cents,
            }
            for i in items
        ],
        "total_cents": total,
        "updated_at": cart.updated_at.isoformat() if cart.updated_at else None,
    }


@bp.get("/cart")
@login_required
def get_cart():
    cart = _get_cart()
    return _cart_response(cart), 200


@bp.post("/cart/add")
@login_required
def add_to_cart():
    data = get_json()
    require_fields(data, ["product_id", "quantity"]) 

    product_id = int(data["product_id"])
    qty = int(data["quantity"])
    if qty <= 0:
        abort_json(400, "validation_error", "Quantity must be > 0")

    product = Product.query.get(product_id)
    if not product or not product.is_active:
        abort_json(404, "not_found", "Product not found")
    if product.stock_qty < qty:
        abort_json(409, "conflict", "Out of stock")

    cart = _get_cart()
    item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
    if item:
        new_qty = item.quantity + qty
        if product.stock_qty < new_qty:
            abort_json(409, "conflict", "Out of stock")
        item.quantity = new_qty
    else:
        item = CartItem(
            cart_id=cart.id,
            product_id=product_id,
            quantity=qty,
            unit_price_cents=product.price_cents,
        )
        db.session.add(item)

    cart.updated_at = datetime.utcnow()
    db.session.commit()
    return _cart_response(cart), 201


@bp.put("/cart/update")
@login_required
def update_cart_item():
    data = get_json()
    require_fields(data, ["product_id", "quantity"])

    product_id = int(data["product_id"])
    qty = int(data["quantity"])

    cart = _get_cart()
    item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
    if not item:
        abort_json(404, "not_found", "Cart item not found")

    if qty <= 0:
        # treat as remove
        db.session.delete(item)
    else:
        product = Product.query.get(product_id)
        if not product or not product.is_active:
            abort_json(404, "not_found", "Product not found")
        if product.stock_qty < qty:
            abort_json(409, "conflict", "Out of stock")
        item.quantity = qty
        item.unit_price_cents = product.price_cents

    cart.updated_at = datetime.utcnow()
    db.session.commit()
    return _cart_response(cart), 200


@bp.delete("/cart/remove")
@login_required
def remove_cart_item():
    data = get_json()
    require_fields(data, ["product_id"])

    product_id = int(data["product_id"])
    cart = _get_cart()
    item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
    if not item:
        return {"message": "no_op"}, 204

    db.session.delete(item)
    cart.updated_at = datetime.utcnow()
    db.session.commit()
    return {"message": "removed"}, 200


@bp.delete("/cart/clear")
@login_required
def clear_cart():
    cart = _get_cart()
    CartItem.query.filter_by(cart_id=cart.id).delete()
    cart.updated_at = datetime.utcnow()
    db.session.commit()
    return {"message": "cleared"}, 200


@bp.get("/cart/validate")
@login_required
def validate_cart():
    cart = _get_cart()
    items = CartItem.query.filter_by(cart_id=cart.id).all()
    issues = []
    for i in items:
        p = Product.query.get(i.product_id)
        if not p or not p.is_active:
            issues.append({"product_id": i.product_id, "issue": "not_found"})
        elif p.stock_qty < i.quantity:
            issues.append({"product_id": i.product_id, "issue": "out_of_stock", "available": p.stock_qty})

    return {"valid": len(issues) == 0, "issues": issues}, 200
