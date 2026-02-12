from datetime import datetime
from db import db

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    addresses = db.relationship(
        "Address",
        backref="user",
        cascade="all, delete-orphan"
    )
    
class Address(db.Model):
    __tablename__ = "addresses"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    label = db.Column(db.String(50), nullable=True)  # Multiple address type field -> Home, Work, etc.
    street_address = db.Column(db.Text, nullable=False)
    postal_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(100), nullable=False)

class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    price_cents = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class CartItem(db.Model):
    __tablename__ = "cart_items"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    user = db.relationship("User", lazy="joined")
    product = db.relationship("Product", lazy="joined")

    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", name="uq_cart_user_product"),
    )

class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    total_cents = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(32), nullable=False, default="placed")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    items = db.relationship(
        "OrderItem",
        backref="order_parent",
        lazy="select",
        cascade="all, delete-orphan"
    )


class OrderItem(db.Model):
    __tablename__ = "order_items"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    unit_price_cents = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    product = db.relationship("Product", lazy="joined")


class PaymentMethod(db.Model):
    __tablename__ = "payment_methods"
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    # Non-sensitive “checkout info” only (NO full card numbers)
    cardholder_name = db.Column(db.String(120), nullable=False)
    brand = db.Column(db.String(40), nullable=False)          # e.g., "Visa"
    last4 = db.Column(db.String(4), nullable=False)           # "1234"
    exp_month = db.Column(db.Integer, nullable=False)         # 1-12
    exp_year = db.Column(db.Integer, nullable=False)          # 2026
    billing_postal = db.Column(db.String(20), nullable=True)

    is_default = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", lazy="joined")

    __table_args__ = (
        db.Index("ix_payment_methods_user_default", "user_id", "is_default"),
    )
