from __future__ import annotations

import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, jsonify, request, session, render_template, redirect, url_for, flash
from dotenv import load_dotenv

from config import Config
from db import db
from models import User, Product, CartItem, Order, OrderItem, PaymentMethod, Address 
from helpers import error, current_user #moved these to their own file to fix circular imports, helpers.py

# Blueprints (API modules)
from routes.auth import bp as auth_bp
from routes.catalog import bp as catalog_bp
from routes.cart import bp as cart_bp
from routes.orders import bp as orders_bp
from routes.options import bp as options_bp
from routes.payment_methods import bp as payment_methods_bp

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
        if request.path.startswith("/api/"):
            return error("bad_request", "Bad request", status=400)
        return render_template("400.html"), 400

    @app.errorhandler(500)
    def server_error(e):
        if request.path.startswith("/api/"):
            return error("server_error", "Unexpected server error", status=500)
        return render_template("500.html"), 500

    @app.context_processor
    def inject_nav():
        """Inject navbar data (user + cart badge count) into all templates."""
        user = current_user()
        if user:
            count = (
                db.session.query(db.func.coalesce(db.func.sum(CartItem.quantity), 0))
                .filter(CartItem.user_id == user.id)
                .scalar()
            )
        else:
            count = sum((session.get("cart") or {}).values())
        return {
            "nav_user": user,
            "nav_cart_count": int(count or 0),
            "current_year": datetime.utcnow().year,
        }

    # --- Web pages (minimal UI) ---
    @app.get("/")
    def home():
        # Homepage: wide layout + featured products.
        featured = Product.query.order_by(Product.id.asc()).limit(4).all()
        categories = [
            {"name": "Wellness", "slug": "wellness", "emoji": "🧘", "count": 3},
            {"name": "Gourmet", "slug": "gourmet", "emoji": "🍷", "count": 4},
            {"name": "Comfort", "slug": "comfort", "emoji": "🛋️", "count": 1},
            {"name": "Baby", "slug": "baby", "emoji": "👶", "count": 1},
            {"name": "Celebration", "slug": "celebration", "emoji": "🎉", "count": 1},
            {"name": "Hobby", "slug": "hobby", "emoji": "🌱", "count": 1},
        ]
        return render_template("home.html", featured=featured, categories=categories)

    @app.get("/products")
    def web_products():
        search = (request.args.get("search") or "").strip()
        category = (request.args.get("category") or "").strip().lower()

        q = Product.query
        # If category is provided but no search, treat category as a search hint.
        if category and not search:
            search = category

        if search:
            like = f"%{search}%"
            q = q.filter(
                db.or_(
                    Product.name.ilike(like),
                    Product.description.ilike(like),
                    Product.sku.ilike(like),
                )
            )

        products = q.order_by(Product.id.asc()).limit(24).all()
        return render_template("products.html", products=products, search=search, category=category)

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
        # Checkout is a 3-step flow: shipping -> payment -> review
        return redirect(url_for("checkout_shipping"))

    # --- Checkout flow (Module 4) ---
    CHECKOUT_TAX_RATE = 0.13

    def _cart_snapshot_for_user(user_id: int):
        """Return (items, summary) for the current user's cart."""
        items = CartItem.query.filter_by(user_id=user_id).all()
        view_items = []
        for ci in items:
            p = ci.product
            if not p:
                continue
            view_items.append(
                {
                    "product_id": p.id,
                    "name": p.name,
                    "image_url": p.image_url,
                    "unit_price_cents": p.price_cents,
                    "quantity": ci.quantity,
                    "line_total_cents": p.price_cents * ci.quantity,
                }
            )

        subtotal = sum(i["line_total_cents"] for i in view_items)
        tax = int(subtotal * CHECKOUT_TAX_RATE)
        shipping = 0
        total = subtotal + tax + shipping
        summary = {
            "subtotal_cents": subtotal,
            "tax_cents": tax,
            "shipping_cents": shipping,
            "total_cents": total,
        }
        return view_items, summary

    @app.get("/checkout/shipping")
    def checkout_shipping():
        user = current_user()
        if not user:
            flash("Please log in to checkout.", "info")
            return redirect(url_for("web_login"))

        items, summary = _cart_snapshot_for_user(user.id)
        if not items:
            flash("Your cart is empty.", "info")
            return redirect(url_for("web_cart"))

        shipping = session.get("checkout_shipping") or {}
        return render_template(
            "checkout_shipping.html",
            items=items,
            summary=summary,
            shipping=shipping,
        )

    @app.post("/checkout/shipping")
    def checkout_shipping_post():
        user = current_user()
        if not user:
            flash("Please log in to checkout.", "info")
            return redirect(url_for("web_login"))

        # Basic validation (keep MVP simple)
        def get(name: str) -> str:
            return (request.form.get(name) or "").strip()

        shipping = {
            "first_name": get("first_name"),
            "last_name": get("last_name"),
            "address": get("address"),
            "city": get("city"),
            "state": get("state"),
            "zip_code": get("zip_code"),
            "phone": get("phone"),
        }

        required = ["first_name", "last_name", "address", "city", "state", "zip_code", "phone"]
        missing = [k for k in required if not shipping.get(k)]
        if missing:
            flash("Please fill in all shipping fields.", "error")
            session["checkout_shipping"] = shipping
            return redirect(url_for("checkout_shipping"))

        session["checkout_shipping"] = shipping
        return redirect(url_for("checkout_payment"))

    @app.get("/checkout/payment")
    def checkout_payment():
        user = current_user()
        if not user:
            flash("Please log in to checkout.", "info")
            return redirect(url_for("web_login"))

        items, summary = _cart_snapshot_for_user(user.id)
        if not items:
            flash("Your cart is empty.", "info")
            return redirect(url_for("web_cart"))

        if not session.get("checkout_shipping"):
            return redirect(url_for("checkout_shipping"))

        methods = (
            PaymentMethod.query.filter_by(user_id=user.id)
            .order_by(PaymentMethod.is_default.desc(), PaymentMethod.id.desc())
            .all()
        )

        selected_id = session.get("checkout_payment_method_id")
        if selected_id and not any(m.id == selected_id for m in methods):
            selected_id = None

        if not selected_id:
            default = next((m for m in methods if m.is_default), None)
            if default:
                selected_id = default.id

        return render_template(
            "checkout_payment.html",
            items=items,
            summary=summary,
            methods=methods,
            selected_id=selected_id,
            user=user,
        )

    @app.post("/checkout/payment")
    def checkout_payment_post():
        user = current_user()
        if not user:
            flash("Please log in to checkout.", "info")
            return redirect(url_for("web_login"))

        if not session.get("checkout_shipping"):
            return redirect(url_for("checkout_shipping"))

        raw = (request.form.get("payment_method_id") or "").strip()
        try:
            payment_method_id = int(raw)
        except Exception:
            payment_method_id = None

        if not payment_method_id:
            flash("Please select a payment method.", "error")
            return redirect(url_for("checkout_payment"))

        pm = PaymentMethod.query.filter_by(id=payment_method_id, user_id=user.id).first()
        if not pm:
            flash("Selected payment method not found.", "error")
            return redirect(url_for("checkout_payment"))

        session["checkout_payment_method_id"] = pm.id
        return redirect(url_for("checkout_review"))

    @app.get("/checkout/review")
    def checkout_review():
        user = current_user()
        if not user:
            flash("Please log in to checkout.", "info")
            return redirect(url_for("web_login"))

        items, summary = _cart_snapshot_for_user(user.id)
        if not items:
            flash("Your cart is empty.", "info")
            return redirect(url_for("web_cart"))

        shipping = session.get("checkout_shipping")
        if not shipping:
            return redirect(url_for("checkout_shipping"))

        payment_method_id = session.get("checkout_payment_method_id")
        if not payment_method_id:
            return redirect(url_for("checkout_payment"))

        pm = PaymentMethod.query.filter_by(id=payment_method_id, user_id=user.id).first()
        if not pm:
            session.pop("checkout_payment_method_id", None)
            return redirect(url_for("checkout_payment"))

        return render_template(
            "checkout_review.html",
            items=items,
            summary=summary,
            shipping=shipping,
            payment_method=pm,
            user=user,
        )

    @app.get("/payment-methods")
    def web_payment_methods():
        user = current_user()
        if not user:
            flash("Please log in to manage payment methods.", "info")
            return redirect(url_for("web_login"))

        methods = (
            PaymentMethod.query.filter_by(user_id=user.id)
            .order_by(PaymentMethod.is_default.desc(), PaymentMethod.id.desc())
            .all()
        )
        return render_template("payment_methods.html", methods=methods)

    @app.post("/payment-methods")
    def web_payment_methods_post():
        user = current_user()
        if not user:
            flash("Please log in to manage payment methods.", "info")
            return redirect(url_for("web_login"))

        def bad(msg: str):
            flash(msg, "error")
            return redirect(url_for("web_payment_methods"))

        cardholder_name = (request.form.get("cardholder_name") or "").strip()
        brand = (request.form.get("brand") or "").strip()
        last4 = (request.form.get("last4") or "").strip()
        exp_month_raw = (request.form.get("exp_month") or "").strip()
        exp_year_raw = (request.form.get("exp_year") or "").strip()
        billing_postal = (request.form.get("billing_postal") or "").strip() or None
        want_default = bool(request.form.get("is_default"))

        if not cardholder_name:
            return bad("Cardholder name is required.")
        if not brand:
            return bad("Card brand is required.")
        if len(last4) != 4 or not last4.isdigit():
            return bad("Last 4 must be exactly 4 digits.")

        try:
            exp_month = int(exp_month_raw)
        except Exception:
            return bad("Exp month must be a number between 1 and 12.")
        if exp_month < 1 or exp_month > 12:
            return bad("Exp month must be between 1 and 12.")

        try:
            exp_year = int(exp_year_raw)
        except Exception:
            return bad("Exp year must be a 4-digit year.")
        year_now = datetime.utcnow().year
        if exp_year < year_now - 1 or exp_year > year_now + 25:
            return bad("Exp year is out of allowed range.")

        pm = PaymentMethod(
            user_id=user.id,
            cardholder_name=cardholder_name,
            brand=brand,
            last4=last4,
            exp_month=exp_month,
            exp_year=exp_year,
            billing_postal=billing_postal,
            is_default=want_default,
        )
        db.session.add(pm)
        db.session.flush()

        count_for_user = PaymentMethod.query.filter_by(user_id=user.id).count()
        if count_for_user == 1:
            want_default = True

        if want_default:
            PaymentMethod.query.filter(
                PaymentMethod.user_id == user.id,
                PaymentMethod.id != pm.id,
                PaymentMethod.is_default.is_(True),
            ).update({"is_default": False})
            pm.is_default = True

        db.session.commit()
        flash("Payment method added.", "success")
        return redirect(url_for("web_payment_methods"))

    @app.get("/orders")
    def web_orders():
        user = current_user()
        if not user:
            flash("Please log in to view your orders.", "info")
            return redirect(url_for("web_login"))
        orders = Order.query.filter_by(user_id=user.id).order_by(Order.id.desc()).all()
        return render_template("orders.html", orders=orders)

    @app.get("/orders/<int:order_id>")
    def web_order_detail(order_id: int):
        user = current_user()
        if not user:
            flash("Please log in to view your order.", "info")
            return redirect(url_for("web_login"))
        order = Order.query.filter_by(id=order_id, user_id=user.id).first()
        if not order:
            return render_template("404.html"), 404
        items = OrderItem.query.filter_by(order_id=order.id).all()
        return render_template("order_detail.html", order=order, items=items)

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
        # Support redirect back to checkout/cart flows.
        redirect_to = (request.args.get("redirect") or request.args.get("next") or request.form.get("redirect") or "").strip()
        if redirect_to.startswith("/") and not redirect_to.startswith("//"):
            return redirect(redirect_to)
        return redirect(url_for("web_products"))

    @app.get("/register")
    def web_register():
        return render_template("register.html")
    
    @app.get("/account")
    def web_account():
        user = current_user()
        if not user:
            return redirect(url_for("web_login"))
        return render_template("account.html", user=user)
    
    @app.post("/account/address")
    def web_add_address():
        user = current_user()
        if not user:
            return redirect(url_for("web_login"))

        address_id = request.form.get("address_id")

        label = (request.form.get("label") or "").strip() or None
        street_address = (request.form.get("street_address") or "").strip()
        postal_code = (request.form.get("postal_code") or "").strip()
        country = (request.form.get("country") or "").strip()

        if not street_address or not postal_code or not country:
            flash("All address fields except label are required.", "error")
            return redirect(url_for("web_account"))

        if address_id:
            address = Address.query.filter_by(id=address_id, user_id=user.id).first()
            if not address:
                flash("Address not found.", "error")
                return redirect(url_for("web_account"))

            address.label = label
            address.street_address = street_address
            address.postal_code = postal_code
            address.country = country

            flash("Address updated successfully.", "success")

        else:
            new_address = Address(
                user_id=user.id,
                label=label,
                street_address=street_address,
                postal_code=postal_code,
                country=country
            )
            db.session.add(new_address)
            flash("Address added successfully.", "success")

        db.session.commit()
        return redirect(url_for("web_account"))
    
    @app.post("/account/address/<int:address_id>/delete")
    def web_delete_address(address_id):
        user = current_user()
        if not user:
            return redirect(url_for("web_login"))

        address = Address.query.filter_by(id=address_id, user_id=user.id).first()

        if not address:
            flash("Address not found.", "error")
            return redirect(url_for("web_account"))

        db.session.delete(address)
        db.session.commit()

        flash("Address deleted successfully.", "success")
        return redirect(url_for("web_account"))
    
    @app.post("/account/phone")
    def web_update_phone():
        user = current_user()
        if not user:
            return redirect(url_for("web_login"))
        country_code = (request.form.get("country_code") or "").strip()
        phone_number = (request.form.get("phone_number") or "").strip()
        if not phone_number:
            user.phone_number = None
        else:
            clean_number = phone_number.replace(" ", "")
            user.phone_number = f"{country_code}{clean_number}"
        db.session.commit()
        flash("Phone number updated.", "success")
        return redirect(url_for("web_account"))

    @app.post("/logout")
    def web_logout():
        session.pop("user_id", None)
        session.pop("checkout_shipping", None)
        session.pop("checkout_payment_method_id", None)
        flash("Logged out.", "success")
        return redirect(url_for("web_products"))

    # --- Register API blueprints under /api ---
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(catalog_bp, url_prefix="/api")
    app.register_blueprint(cart_bp, url_prefix="/api")
    app.register_blueprint(orders_bp, url_prefix="/api")
    app.register_blueprint(options_bp, url_prefix="/api")
    app.register_blueprint(payment_methods_bp, url_prefix="/api")

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
