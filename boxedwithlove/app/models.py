from __future__ import annotations

from datetime import datetime
from sqlalchemy import UniqueConstraint, Index

from boxedwithlove.app.extensions import db


class Account(db.Model):
    __tablename__ = "accounts"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    addresses = db.relationship("Address", backref="account", lazy=True, cascade="all, delete-orphan")
    payment_methods = db.relationship("PaymentMethod", backref="account", lazy=True, cascade="all, delete-orphan")
    orders = db.relationship("Order", backref="account", lazy=True)


class Address(db.Model):
    __tablename__ = "addresses"

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False, index=True)

    street = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    province = db.Column(db.String(100), nullable=True)
    postal_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(100), nullable=False)


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(64), nullable=False, unique=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=False)  # boxes | baskets | fillers
    price_cents = db.Column(db.Integer, nullable=False)
    stock_qty = db.Column(db.Integer, nullable=False, default=0)
    image_url = db.Column(db.String(1024), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    reviews = db.relationship("Review", backref="product", lazy=True, cascade="all, delete-orphan")


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False, index=True)

    star = db.Column(db.Integer, nullable=True)  # 1..5
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_reviews_product_created", "product_id", "created_at"),
    )


class Cart(db.Model):
    __tablename__ = "carts"

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False, unique=True, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    items = db.relationship("CartItem", backref="cart", lazy=True, cascade="all, delete-orphan")


class CartItem(db.Model):
    __tablename__ = "cart_items"

    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey("carts.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price_cents = db.Column(db.Integer, nullable=False)  # snapshot for speed

    __table_args__ = (
        UniqueConstraint("cart_id", "product_id", name="uq_cart_item_cart_product"),
        Index("ix_cart_items_cart", "cart_id"),
    )


class PaymentMethod(db.Model):
    __tablename__ = "payment_methods"

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False, index=True)

    # Non-sensitive placeholders (NO full PAN)
    brand = db.Column(db.String(50), nullable=False)  # e.g., VISA
    last4 = db.Column(db.String(4), nullable=False)
    exp_month = db.Column(db.Integer, nullable=False)
    exp_year = db.Column(db.Integer, nullable=False)
    billing_postal_code = db.Column(db.String(20), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False, index=True)
    payment_method_id = db.Column(db.Integer, db.ForeignKey("payment_methods.id"), nullable=True)

    status = db.Column(db.String(30), nullable=False, default="PLACED")
    total_cents = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    items = db.relationship("OrderItem", backref="order", lazy=True, cascade="all, delete-orphan")


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price_cents = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        Index("ix_order_items_order", "order_id"),
    )
