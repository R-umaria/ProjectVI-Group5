# run with: docker compose exec web pytest tests/test_cart_module.py -v

import json
from models import Product, Category, User, CartItem

def login(client_cart):

    return client_cart.post("/api/auth/login",
                      json={"email": "test@test.com", "password": "Test123!"})


# CART-001: add product to cart (logged in)
def test_add_to_cart_logged_in(client_cart):
    login(client_cart)
    
    response = client_cart.post("/api/cart/items", json={"product_id": 1, "quantity": 2})
    
    assert response.status_code == 201
    assert response.json["success"] == True
    cart = client_cart.get("/api/cart").json
    assert len(cart["items"]) == 1
    assert cart["items"][0]["quantity"] == 2


# CART-002: add product to cart (not logged in)
def test_add_to_cart_guest(client_cart):
    response = client_cart.post("/api/cart/items", json={"product_id": 1, "quantity": 3})
    
    assert response.status_code == 201
    
    cart = client_cart.get("/api/cart").json
    assert len(cart["items"]) == 1
    assert "session_" in str(cart["items"][0]["id"])


# CART-003: get cart shows correct totals
def test_get_cart_totals(client_cart):
    login(client_cart)
    # grab products from DB
    p1 = Product.query.filter_by(sku="TEST1").first()
    p2 = Product.query.filter_by(sku="TEST2").first()

    client_cart.post("/api/cart/items", json={"product_id": p1.id, "quantity": 2})
    client_cart.post("/api/cart/items", json={"product_id": p2.id, "quantity": 1})
    
    cart = client_cart.get("/api/cart").json
    
    assert len(cart["items"]) == 2
    assert cart["summary"]["subtotal_cents"] == 10997  # 2999*2 + 4999
    assert cart["summary"]["tax_cents"] == 1429        # 13% of subtotal
    assert cart["summary"]["total_cents"] == 12426


# CART-004: update cart item with PUT
def test_update_cart_put(client_cart):
    login(client_cart)
    client_cart.post("/api/cart/items", json={"product_id": 1, "quantity": 2})
    
    cart = client_cart.get("/api/cart").json
    item_id = cart["items"][0]["id"]
    
    response = client_cart.put(f"/api/cart/items/{item_id}", json={"quantity": 5})
    
    assert response.status_code == 200
    cart = client_cart.get("/api/cart").json
    assert cart["items"][0]["quantity"] == 5


# CART-005: Update cart item with PATCH
def test_update_cart_patch(client_cart):
    login(client_cart)
    client_cart.post("/api/cart/items", json={"product_id": 1, "quantity": 3})
    
    cart = client_cart.get("/api/cart").json
    item_id = cart["items"][0]["id"]
    
    client_cart.patch(f"/api/cart/items/{item_id}", json={"quantity": 7})
    
    cart = client_cart.get("/api/cart").json
    assert cart["items"][0]["quantity"] == 7


# CART-006: delete cart item
def test_delete_cart_item(client_cart):
    login(client_cart)
    client_cart.post("/api/cart/items", json={"product_id": 1, "quantity": 1})
    
    cart = client_cart.get("/api/cart").json
    item_id = cart["items"][0]["id"]
    
    response = client_cart.delete(f"/api/cart/items/{item_id}")
    
    assert response.status_code == 200
    cart = client_cart.get("/api/cart").json
    assert len(cart["items"]) == 0

# CART-007: Session cart merges on login
def test_session_merges_on_login(client_cart):
    # Add to session cart
    client_cart.post("/api/cart/items", json={"product_id": 1, "quantity": 2})
    
    # Login
    login(client_cart)
    
    # Check cart merged
    cart = client_cart.get("/api/cart").json
    assert len(cart["items"]) == 1
    assert cart["items"][0]["quantity"] == 2
    assert isinstance(cart["items"][0]["id"], int)  # DB id, not session


# CART-008: Adding same product increases quantity
def test_add_same_product_increases_quantity(client_cart):
    login(client_cart)
    client_cart.post("/api/cart/items", json={"product_id": 1, "quantity": 2})
    client_cart.post("/api/cart/items", json={"product_id": 1, "quantity": 3})
    
    cart = client_cart.get("/api/cart").json
    assert len(cart["items"]) == 1
    assert cart["items"][0]["quantity"] == 5