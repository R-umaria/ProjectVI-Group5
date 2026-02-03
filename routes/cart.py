from flask import Blueprint, request, session

from db import db
from models import CartItem, Product
from app import error

bp = Blueprint("cart_api", __name__)

def require_user_id():
    uid = session.get("user_id")
    if not uid:
        return None, error("unauthorized", "login required", 401)
    return uid, None

@bp.get("/cart")
def get_cart():
    uid, err = require_user_id()
    if err:
        return err
    items = CartItem.query.filter_by(user_id=uid).all()
    return {
        "items": [
            {
                "id": i.id,
                "product_id": i.product_id,
                "name": i.product.name,
                "unit_price_cents": i.product.price_cents,
                "quantity": i.quantity,
            } for i in items
        ]
    }, 200

@bp.post("/cart/items")
def add_item():
    uid, err = require_user_id()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    quantity = data.get("quantity", 1)

    if not isinstance(product_id, int) or not isinstance(quantity, int) or quantity < 1:
        return error("validation_error", "product_id must be int; quantity must be int >= 1", 400)

    product = Product.query.get(product_id)
    if not product:
        return error("not_found", "product not found", 404)

    existing = CartItem.query.filter_by(user_id=uid, product_id=product_id).first()
    if existing:
        existing.quantity += quantity
        db.session.commit()
        return {"id": existing.id, "quantity": existing.quantity}, 200

    item = CartItem(user_id=uid, product_id=product_id, quantity=quantity)
    db.session.add(item)
    db.session.commit()
    return {"id": item.id, "quantity": item.quantity}, 201

@bp.put("/cart/items/<int:item_id>")
def replace_item(item_id: int):
    uid, err = require_user_id()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    quantity = data.get("quantity")
    if not isinstance(quantity, int) or quantity < 1:
        return error("validation_error", "quantity must be int >= 1", 400)

    item = CartItem.query.filter_by(id=item_id, user_id=uid).first()
    if not item:
        return error("not_found", "cart item not found", 404)

    item.quantity = quantity
    db.session.commit()
    return {"id": item.id, "quantity": item.quantity}, 200

@bp.patch("/cart/items/<int:item_id>")
def patch_item(item_id: int):
    uid, err = require_user_id()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    quantity = data.get("quantity")
    if quantity is None:
        return error("validation_error", "nothing to update", 400)
    if not isinstance(quantity, int) or quantity < 1:
        return error("validation_error", "quantity must be int >= 1", 400)

    item = CartItem.query.filter_by(id=item_id, user_id=uid).first()
    if not item:
        return error("not_found", "cart item not found", 404)

    item.quantity = quantity
    db.session.commit()
    return {"id": item.id, "quantity": item.quantity}, 200

@bp.delete("/cart/items/<int:item_id>")
def delete_item(item_id: int):
    uid, err = require_user_id()
    if err:
        return err

    item = CartItem.query.filter_by(id=item_id, user_id=uid).first()
    if not item:
        return error("not_found", "cart item not found", 404)

    db.session.delete(item)
    db.session.commit()
    return {"ok": True}, 200
