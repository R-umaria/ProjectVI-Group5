import os
import pytest

from app import create_app
from db import db

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
