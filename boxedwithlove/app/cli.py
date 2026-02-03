from __future__ import annotations

from flask import Blueprint
from werkzeug.security import generate_password_hash

from boxedwithlove.app.extensions import db
from boxedwithlove.app.models import Account, Product, Cart

cli_bp = Blueprint("cli", __name__)


@cli_bp.cli.command("seed")
def seed_data() -> None:
    """Seed minimal dev data.

    Safe to run multiple times; it will no-op if data exists.
    """

    if not Account.query.filter_by(email="user@example.com").first():
        user = Account(
            email="user@example.com",
            password_hash=generate_password_hash("Password123!"),
            first_name="Demo",
            last_name="User",
            phone_number="555-0100",
        )
        db.session.add(user)
        db.session.flush()
        db.session.add(Cart(account_id=user.id))

    if Product.query.count() == 0:
        products = [
            Product(sku="BOX-001", name="Classic Gift Box", description="A sturdy box.", category="boxes", price_cents=2999, stock_qty=100),
            Product(sku="BASK-001", name="Wicker Basket", description="A wicker basket.", category="baskets", price_cents=4999, stock_qty=80),
            Product(sku="FILL-001", name="Chocolate Fillers", description="Assorted chocolates.", category="fillers", price_cents=1299, stock_qty=300),
        ]
        db.session.add_all(products)

    db.session.commit()
    print("Seed complete. Login: user@example.com / Password123!")
