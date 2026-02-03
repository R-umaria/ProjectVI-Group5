"""Minimal server-rendered UI placeholders.

UI exists to satisfy SYS-060 (quality/accessibility/usability), but focus is on API + performance.
"""

from flask import Blueprint, render_template

ui_bp = Blueprint("ui", __name__)

@ui_bp.get("/")
def home():
    return render_template("pages/home.html")

@ui_bp.get("/catalog")
def catalog_page():
    return render_template("pages/catalog.html")

@ui_bp.get("/cart")
def cart_page():
    return render_template("pages/cart.html")

@ui_bp.get("/checkout")
def checkout_page():
    return render_template("pages/checkout.html")

@ui_bp.get("/login")
def login_page():
    return render_template("pages/login.html")

@ui_bp.get("/register")
def register_page():
    return render_template("pages/register.html")
