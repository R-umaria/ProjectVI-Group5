from __future__ import annotations

import logging
from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from boxedwithlove.app.config import Config
from boxedwithlove.app.extensions import db, migrate, cors
from boxedwithlove.app.common.errors import ApiError
from boxedwithlove.app.common.request_context import init_request_id
from boxedwithlove.app.api.register import register_api_blueprints
from boxedwithlove.app.cli import cli_bp


def create_app(config_object: type[Config] = Config) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object)

    # Basic logging (enough for perf debugging)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    # Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS") or "*"}})

    # Request id
    @app.before_request
    def _before_request():
        init_request_id()

    # Health endpoint (for Docker/JMeter)
    @app.get("/health")
    def health():
        return {"status": "ok"}, 200

    # Register API blueprints
    register_api_blueprints(app)

    # CLI (flask seed)
    app.register_blueprint(cli_bp)

    # Simple UI landing page
    @app.get("/")
    def index():
        return (
            "<h1>BoxedWithLove</h1><p>Server is running. Visit <a href='/api'>/api</a>.</p>",
            200,
            {"Content-Type": "text/html"},
        )

    # Error handlers
    @app.errorhandler(ApiError)
    def handle_api_error(err: ApiError):
        from flask import g

        return jsonify(err.to_dict(getattr(g, "request_id", None))), err.status_code

    @app.errorhandler(HTTPException)
    def handle_http_exception(err: HTTPException):
        from flask import g

        # Normalize Werkzeug errors into our JSON shape
        payload = {
            "error": {
                "code": "http_error",
                "message": err.description,
                "details": {"name": err.name},
                "request_id": getattr(g, "request_id", None),
            }
        }
        return jsonify(payload), err.code or 500

    @app.errorhandler(Exception)
    def handle_unexpected(err: Exception):
        app.logger.exception("Unhandled exception")
        from flask import g

        payload = {
            "error": {
                "code": "internal_error",
                "message": "Internal server error",
                "details": {},
                "request_id": getattr(g, "request_id", None),
            }
        }
        return jsonify(payload), 500

    return app
