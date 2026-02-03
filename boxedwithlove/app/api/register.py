from flask import Flask

from boxedwithlove.modules.auth.routes import bp as auth_bp
from boxedwithlove.modules.catalog.routes import bp as catalog_bp
from boxedwithlove.modules.cart.routes import bp as cart_bp
from boxedwithlove.modules.orders.routes import bp as orders_bp


def register_api_blueprints(app: Flask) -> None:
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(catalog_bp, url_prefix="/api")
    app.register_blueprint(cart_bp, url_prefix="/api")
    app.register_blueprint(orders_bp, url_prefix="/api")

    # Root API document
    @app.get("/api")
    def api_index():
        return {
            "name": "BoxedWithLove API",
            "version": "0.1.0",
            "endpoints": {
                "auth": ["/users", "/auth/login", "/auth/logout", "/users/me"],
                "catalog": ["/products", "/products/<id>", "/products/<id>/reviews"],
                "cart": ["/cart", "/cart/add", "/cart/update", "/cart/remove", "/cart/clear", "/cart/validate"],
                "orders": ["/payment-methods", "/orders"],
            },
        }, 200
