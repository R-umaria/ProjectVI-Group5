from __future__ import annotations

import os
import csv
import re
from pathlib import Path
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, jsonify, request, session, render_template, redirect, url_for, flash
from dotenv import load_dotenv

from config import Config
from db import db
from models import User, Product, CartItem, Order, OrderItem, PaymentMethod, Category, Review
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
        category = (request.args.get("category") or "").strip()
        sort = (request.args.get("sort") or "popular").strip()

        q = Product.query

        if search:
            like = f"%{search}%"
            q = q.filter(
                db.or_(
                    Product.name.ilike(like),
                    Product.description.ilike(like),
                    Product.sku.ilike(like),
                )
            )

        if category:
            q = q.join(Category).filter(db.func.lower(Category.category_name) == category.lower())

        if sort == "price_asc":
            q = q.order_by(Product.price_cents.asc(), Product.id.asc())
        elif sort == "price_desc":
            q = q.order_by(Product.price_cents.desc(), Product.id.asc())
        elif sort == "newest":
            q = q.order_by(Product.created_at.desc(), Product.id.desc())
        else:
            q = q.order_by(Product.id.asc())

        products = q.limit(24).all()
        categories = Category.query.order_by(Category.category_name.asc()).all()

        return render_template(
            "products.html",
            products=products,
            categories=categories,
            search=search,
            category=category,
            sort=sort,
        )

    @app.get("/products/<int:product_id>")
    def web_product_detail(product_id: int):
        product = Product.query.get_or_404(product_id)

        reviews = db.relationship("Review", back_populates="product", cascade="all, delete-orphan", lazy="select")

        reviews = (
            Review.query.filter(Review.product_id == product_id)
            .order_by(Review.review_date.desc(), Review.id.desc())
            .all()
        )

        avg_rating = (
            db.session.query(db.func.avg(Review.rating))
            .filter(Review.product_id == product_id)
            .scalar()
        )
        avg_rating = float(avg_rating) if avg_rating is not None else 0.0

        return render_template(
            "product_detail.html",
            product=product,
            reviews=reviews,
            avg_rating=avg_rating,
        )

    @app.post("/products/<int:product_id>/reviews")
    def web_post_review(product_id: int):
        user = current_user()
        if not user:
            flash("Please log in to leave a review.", "info")
            return redirect(url_for("web_login"))

        product = Product.query.get(product_id)
        if not product:
            return render_template("404.html"), 404

        rating_raw = (request.form.get("rating") or "").strip()
        comment = (request.form.get("comment") or "").strip() or None

        try:
            rating = int(rating_raw)
        except Exception:
            rating = 0

        if rating < 1 or rating > 5:
            flash("Rating must be between 1 and 5.", "error")
            return redirect(url_for("web_product_detail", product_id=product_id))

        r = Review(user_id=user.id, product_id=product_id, rating=rating, comment=comment)
        db.session.add(r)
        db.session.commit()

        flash("Thanks! Your review was submitted.", "success")
        return redirect(url_for("web_product_detail", product_id=product_id))

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
        """Seed database with products (CSV if present, otherwise minimal demo data)."""
        with app.app_context():
            db.create_all()

            # Prevent accidental duplication
            if Product.query.count() > 0:
                print("Products already exist. Reset DB (docker compose down -v) to reseed.")
                return
            csv_path = Path(__file__).resolve().parent / "products.csv"
            # Product images live under static/images/products/
            images_dir = Path(__file__).resolve().parent / "static" / "images" / "products"

            def parse_price_cents(raw: str) -> int:
                raw = (raw or "").strip()
                if not raw:
                    return 0
                if "." in raw:
                    return int(round(float(raw) * 100))
                return int(raw)

            def slug_sku(name: str, used: set[str]) -> str:
                base = re.sub(r"[^A-Za-z0-9]+", "", (name or "").upper())[:10] or "ITEM"
                sku = f"BWL-{base}"
                i = 2
                while sku in used:
                    sku = f"BWL-{base}-{i}"
                    i += 1
                used.add(sku)
                return sku

            def resolve_image_url(product_name: str, image_field: str | None) -> str | None:
                image_field = (image_field or "").strip()

                # If someone later puts a real URL in the CSV, accept it
                if image_field.startswith("http://") or image_field.startswith("https://"):
                    return image_field

                # If CSV contains a real filename like Basket01.jpg, use it (if exists)
                if image_field and "." in image_field:
                    p = images_dir / image_field
                    if p.exists():
                        return f"/static/images/products/{p.name}"

                # Fast path: build a case-insensitive stem->filename map once
                # (handles .jpg/.png/.webp and any casing)
                if not hasattr(resolve_image_url, "_stem_map"):
                    stem_map = {}
                    if images_dir.exists():
                        for fp in images_dir.iterdir():
                            if fp.is_file():
                                stem_map[fp.stem.lower()] = fp.name
                    setattr(resolve_image_url, "_stem_map", stem_map)

                stem_map = getattr(resolve_image_url, "_stem_map")
                hit = stem_map.get((product_name or "").strip().lower())
                if hit:
                    return f"/static/images/products/{hit}"

                # Auto-match: ProductName + common extensions
                base = (product_name or "").strip()
                candidates = []
                for ext in (".jpg", ".jpeg", ".png", ".webp"):
                    candidates.append(base + ext)
                    candidates.append(base.lower() + ext)
                    candidates.append(base.upper() + ext)

                for c in candidates:
                    p = images_dir / c
                    if p.exists():
                        return f"/static/images/products/{p.name}"

                return None  # ok; UI will show placeholder

            # Create categories lazily
            categories_by_name: dict[str, Category] = {}

            used_skus: set[str] = set()

            if csv_path.exists():
                print(f"Seeding from CSV: {csv_path}")
                with open(csv_path, newline="", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)

                    for row in reader:
                        name = (row.get("ProductName") or "").strip()
                        if not name:
                            continue

                        category_name = (row.get("Category") or "").strip() or "General"
                        if category_name not in categories_by_name:
                            cat = Category(category_name=category_name)
                            db.session.add(cat)
                            categories_by_name[category_name] = cat

                        price_cents = parse_price_cents(row.get("ProductPrice"))
                        desc = (row.get("Description") or "").strip()
                        image_url = resolve_image_url(name, row.get("Image_URL"))

                        p = Product(
                            sku=slug_sku(name, used_skus),
                            name=name,
                            description=desc,
                            price_cents=price_cents,
                            image_url=image_url,
                            category=categories_by_name[category_name],
                            stock=50,
                            is_available=True,
                        )
                        db.session.add(p)

                db.session.commit()
                print(f"Seeded {Product.query.count()} products.")
                return

            # Fallback minimal seed if CSV missing
            print("products.csv not found, seeding minimal demo products.")
            cat = Category(category_name="General")
            db.session.add(cat)
            db.session.add_all([
                Product(sku="BWL-001", name="Cozy Winter Box", description="Hot cocoa, socks, and a candle.", price_cents=3999, image_url="", category=cat, stock=25, is_available=True),
                Product(sku="BWL-002", name="Self-Care Basket", description="Bath bombs, tea, and skincare minis.", price_cents=4999, image_url="", category=cat, stock=18, is_available=True),
                Product(sku="BWL-003", name="Snack Attack Box", description="Gourmet snacks for sharing.", price_cents=2999, image_url="", category=cat, stock=30, is_available=True),
            ])
            db.session.commit()

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
