from flask import Blueprint, jsonify, request, session
from db import db
from models import Product, CartItem

bp = Blueprint("cart", __name__)

# for users who arent logged in yet, get the cart items from the session
def get_session_cart():
    return session.get("cart", {})

# save cart items to session
def set_session_cart(cart_data):
    session["cart"] = cart_data

@bp.get("/cart")
#get all items in cart, for both loggedin and non logged in users
def get_cart():
    user_id = session.get("user_id")
    
    if user_id:
        # logged in users - get cart info from database
        items = CartItem.query.filter_by(user_id=user_id).all()
        cart_items = []
        for item in items:
            cart_items.append({
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product.name,
                "product_description": item.product.description,
                "product_image": item.product.image_url,
                "price_cents": item.product.price_cents,
                "quantity": item.quantity,
                "subtotal_cents": item.product.price_cents * item.quantity
            })
    else:
        # non logged in, get from session
        cart = get_session_cart()
        cart_items = []
        for product_id_str, quantity in cart.items():
            product = Product.query.get(int(product_id_str))
            if product:
                cart_items.append({
                    "id": f"session_{product_id_str}",
                    "product_id": product.id,
                    "product_name": product.name,
                    "product_description": product.description,
                    "product_image": product.image_url,
                    "price_cents": product.price_cents,
                    "quantity": quantity,
                    "subtotal_cents": product.price_cents * quantity
                })
    
    # calculate totals
    subtotal = sum(item["subtotal_cents"] for item in cart_items)
    tax = int(subtotal * 0.13)  # 13% tax
    total = subtotal + tax
    
    return jsonify({
        "items": cart_items,
        "summary": {
            "subtotal_cents": subtotal,
            "tax_cents": tax,
            "shipping_cents": 0,
            "total_cents": total
        }
    })

@bp.post("/cart/items")
# add product to cart
def add_to_cart():
    data = request.get_json()
    product_id = data.get("product_id")
    quantity = data.get("quantity", 1)

    if not product_id:
        return jsonify({"error": {"code": "missing_product", "message": "Product ID required"}}), 400
    
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": {"code": "not_found", "message": "Product not found"}}), 404
    
    user_id = session.get("user_id")
    
    if user_id:
        # for logged in users - save to database
        existing = CartItem.query.filter_by(user_id=user_id, product_id=product_id).first()
        if existing:
            existing.quantity += quantity
        else:
            item = CartItem(user_id=user_id, product_id=product_id, quantity=quantity)
            db.session.add(item)
        db.session.commit()
    else:
        # non logged in user - save to session
        cart = get_session_cart()
        cart_key = str(product_id)
        cart[cart_key] = cart.get(cart_key, 0) + quantity
        set_session_cart(cart)
    
    return jsonify({"success": True, "message": "Item added to cart"}), 201

@bp.put("/cart/items/<item_id>")
# replaces the quanitity of the cart item - PUT
def update_cart_item(item_id):
    data = request.get_json()
    quantity = data.get("quantity")
    
    if quantity is None or quantity < 1:
        return jsonify({"error": {"code": "invalid_quantity", "message": "Quantity must be at least 1"}}), 400
    
    user_id = session.get("user_id")
    
    if user_id and not item_id.startswith("session_"):
        # database cart item
        item = CartItem.query.filter_by(id=item_id, user_id=user_id).first()
        if not item:
            return jsonify({"error": {"code": "not_found", "message": "Cart item not found"}}), 404
        item.quantity = quantity
        db.session.commit()
    else:
        # session
        product_id = item_id.replace("session_", "")
        cart = get_session_cart()
        if product_id not in cart:
            return jsonify({"error": {"code": "not_found", "message": "Cart item not found"}}), 404
        cart[product_id] = quantity
        set_session_cart(cart)
    
    return jsonify({"success": True, "message": "Cart updated"})

@bp.patch("/cart/items/<item_id>")
def partial_update_cart_item(item_id):
    data = request.get_json()
    quantity = data.get("quantity")
    
    if quantity is not None and quantity < 1:
        return jsonify({"error": {"code": "invalid_quantity", "message": "Quantity must be at least 1"}}), 400
    
    user_id = session.get("user_id")
    
    if user_id and not item_id.startswith("session_"):
        # database cart item
        item = CartItem.query.filter_by(id=item_id, user_id=user_id).first()
        if not item:
            return jsonify({"error": {"code": "not_found", "message": "Cart item not found"}}), 404
        if quantity is not None:
            item.quantity = quantity
        db.session.commit()
    else:
        # session
        product_id = item_id.replace("session_", "")
        cart = get_session_cart()
        if product_id not in cart:
            return jsonify({"error": {"code": "not_found", "message": "Cart item not found"}}), 404
        if quantity is not None:
            cart[product_id] = quantity
        set_session_cart(cart)
    
    return jsonify({"success": True, "message": "Cart updated"})


@bp.delete("/cart/items/<item_id>")
# delete from cart
def delete_cart_item(item_id):
    user_id = session.get("user_id")
    
    if user_id and not item_id.startswith("session_"):
        # database cart item
        item = CartItem.query.filter_by(id=item_id, user_id=user_id).first()
        if not item:
            return jsonify({"error": {"code": "not_found", "message": "Cart item not found"}}), 404
        db.session.delete(item)
        db.session.commit()
    else:
        # session cart item
        product_id = item_id.replace("session_", "")
        cart = get_session_cart()
        if product_id in cart:
            del cart[product_id]
            set_session_cart(cart)
        else:
            return jsonify({"error": {"code": "not_found", "message": "Cart item not found"}}), 404
    
    return jsonify({"success": True, "message": "Item removed from cart"})