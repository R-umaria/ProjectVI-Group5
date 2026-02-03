from flask import Blueprint, jsonify, make_response

bp = Blueprint("options_api", __name__)

@bp.route("/options", methods=["OPTIONS"])
def options_route():
    # This exists to satisfy the course requirement that the API supports OPTIONS.
    resp = make_response("", 204)
    resp.headers["Allow"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return resp
