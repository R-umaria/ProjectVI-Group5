from __future__ import annotations

import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, jsonify, request, session, render_template, redirect, url_for, flash
from dotenv import load_dotenv

from config import Config
from db import db
from models import User, Product, CartItem, Order, OrderItem
from helpers import error, current_user #moved these to their own file to fix circular imports, helpers.py

# Blueprints (API modules)
from routes.auth import bp as auth_bp
from routes.catalog import bp as catalog_bp
from routes.cart import bp as cart_bp
from routes.orders import bp as orders_bp
from routes.options import bp as options_bp

load_dotenv()

def create_app() -> Flask:
    global error, current_user
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)

    db.init_app(app)

    # --- Standard JSON error schema ---
    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return error("not_found", "Resource not found", status=404)
        return render_template("404.html"), 404

    @app.errorhandler(400)
    def bad_request(e):
        return error("bad_request", "Bad request", status=400)

    @app.errorhandler(500)
    def server_error(e):
        return error("server_error", "Unexpected server error", status=500)

    # --- Web pages (minimal UI) ---
    @app.get("/")
    def home():
        return redirect(url_for("web_products"))

    @app.get("/products")
    def web_products():
        products = Product.query.order_by(Product.id.asc()).limit(24).all()
        return render_template("products.html", products=products)

    @app.get("/products/<int:product_id>")
    def web_product_detail(product_id: int):
        product = Product.query.get_or_404(product_id)
        return render_template("product_detail.html", product=product)

    @app.get("/cart")
    def web_cart():
        return render_template("cart.html")

    @app.get("/checkout")
    def web_checkout():
        user = current_user()
        if not user:
            flash("Please log in to checkout.", "info")
            return redirect(url_for("web_login"))
        return render_template("checkout.html")

    @app.get("/login")
    def web_login():
        return render_template("login.html")

    @app.post("/login")
    def web_login_post():
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            flash("Invalid email or password.", "error")
            return redirect(url_for("web_login"))
        session["user_id"] = user.id

        # added this so not logged in users can still create a cart, when they
        # eventually log in, it gets merged to their user cart though - andy
        session_cart_to_user(user.id) 

        flash("Logged in.", "success")
        return redirect(url_for("web_products"))

    @app.get("/register")
    def web_register():
        return render_template("register.html")

    @app.post("/register")
    def web_register_post():
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        if not email or not password:
            flash("Email and password are required.", "error")
            return redirect(url_for("web_register"))
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "error")
            return redirect(url_for("web_register"))
        user = User(email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        session["user_id"] = user.id
        flash("Account created.", "success")
        return redirect(url_for("web_products"))

    @app.post("/logout")
    def web_logout():
        session.pop("user_id", None)
        flash("Logged out.", "success")
        return redirect(url_for("web_products"))

    # --- Register API blueprints under /api ---
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(catalog_bp, url_prefix="/api")
    app.register_blueprint(cart_bp, url_prefix="/api")
    app.register_blueprint(orders_bp, url_prefix="/api")
    app.register_blueprint(options_bp, url_prefix="/api")

    # --- CLI commands (simple) ---
    @app.cli.command("init-db")
    def init_db_cmd():
        """Create tables."""
        with app.app_context():
            db.create_all()
        print("DB initialized (tables created).")

    @app.cli.command("seed")
    def seed_cmd():
        """Insert a few sample products for demos/tests."""
        with app.app_context():
            db.create_all()
            if Product.query.count() == 0:
                samples = [
                    Product(sku="BWL-001", name="Cozy Winter Box", description="Hot cocoa, socks, and a candle.", price_cents=3999, image_url=""),
                    Product(sku="BWL-002", name="Self-Care Basket", description="Bath bombs, tea, and skincare minis.", price_cents=4999, image_url=""),
                    Product(sku="BWL-003", name="Snack Attack Box", description="Gourmet snacks for sharing.", price_cents=2999, image_url=""),
                ]
                db.session.add_all(samples)
                db.session.commit()
                print("Seeded products.")
            else:
                print("Products already exist; skipping seed.")

    return app

# merges the session cart into users database cart when they log in or register, 
# so that non logged in users can still make a cart and it will sync to their account upon login/register
def session_cart_to_user(user_id: int):
    session_cart = session.get("cart", {})
    
    if not session_cart:
        return
    
    for product_id_str, quantity in session_cart.items():
        product_id = int(product_id_str)
        
        # see if item is already in someones cart
        existing = CartItem.query.filter_by(user_id=user_id, product_id=product_id).first()
        if existing:
            #update the quanitiy if it is already there
            existing.quantity += quantity
        else:
            #if not, add a new item
            new_item = CartItem(user_id=user_id, product_id=product_id, quantity=quantity)
            db.session.add(new_item)
    
    db.session.commit()
    # clear the sessions cart after done merging
    session.pop("cart", None)


#-----moved these to their own file, check in helpers.py!!-----

# def error(code: str, message: str, status: int = 400, details: dict | None = None):
#     payload = {"error": {"code": code, "message": message}}
#     if details is not None:
#         payload["error"]["details"] = details
#     return jsonify(payload), status


# def current_user() -> User | None:
#     uid = session.get("user_id")
#     if not uid:
#         return None
#     return User.query.get(uid)


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")), debug=True)
