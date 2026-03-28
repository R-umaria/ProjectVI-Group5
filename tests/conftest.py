import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from db import db
from models import User, Product, Category, CartItem
from werkzeug.security import generate_password_hash

@pytest.fixture()
def client():
    # Use SQLite in tests for simplicity.
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    app = create_app()
    app.config["TESTING"] = True

    with app.app_context():
        db.create_all()

    with app.test_client() as client:
        yield client


# create another test client using existing database (for the cart tests)
@pytest.fixture()
def client_cart():
    app = create_app()
    app.config["TESTING"] = True
    
    with app.app_context():
        # delete stuff from previous tests
        CartItem.query.delete()
        
        # find/create test category
        cat = Category.query.filter_by(category_name="TestCategory").first()
        if not cat:
            cat = Category(category_name="TestCategory")
            db.session.add(cat)
            db.session.commit()
        
        # find/create test products
        p1 = Product.query.filter_by(sku="TEST1").first()
        if not p1:
            p1 = Product(sku="TEST1", name="Product 1", description="Desc 1", 
                        price_cents=2999, stock=100, category_id=cat.id)
            db.session.add(p1)
        
        p2 = Product.query.filter_by(sku="TEST2").first()
        if not p2:
            p2 = Product(sku="TEST2", name="Product 2", description="Desc 2", 
                        price_cents=4999, stock=50, category_id=cat.id)
            db.session.add(p2)
        
        # find/create test user
        user = User.query.filter_by(email="test@test.com").first()
        if not user:
            user = User(
                email="test@test.com",
                password_hash=generate_password_hash("Test123!")
            )
            db.session.add(user)
        
        db.session.commit()

    with app.test_client() as client_cart:
        yield client_cart
    
    with app.app_context():
        CartItem.query.delete()
        db.session.commit()
