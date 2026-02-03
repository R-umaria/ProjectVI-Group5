from __future__ import annotations

from flask import Blueprint, request, session
from sqlalchemy import func

from boxedwithlove.app.extensions import db
from boxedwithlove.app.models import Product, Review
from boxedwithlove.app.common.errors import abort_json
from boxedwithlove.app.common.validation import get_json, require_fields
from boxedwithlove.app.common.auth import login_required

bp = Blueprint("catalog", __name__)


@bp.get("/products")
def list_products():
    """GET /api/products - Retrieve all products.

    Query params:
      - category: boxes|baskets|fillers
      - limit, offset
    """
    category = request.args.get("category")
    limit = min(int(request.args.get("limit", "20")), 100)
    offset = int(request.args.get("offset", "0"))

    q = Product.query.filter_by(is_active=True)
    if category:
        q = q.filter_by(category=category)

    items = q.order_by(Product.id.asc()).offset(offset).limit(limit).all()

    return {
        "items": [
            {
                "id": p.id,
                "sku": p.sku,
                "name": p.name,
                "category": p.category,
                "price_cents": p.price_cents,
                "stock_qty": p.stock_qty,
                "image_url": p.image_url,
            }
            for p in items
        ],
        "pagination": {"limit": limit, "offset": offset, "count": len(items)},
    }, 200


@bp.get("/products/<int:product_id>")
def get_product(product_id: int):
    """GET /api/products/<id> - Retrieve product details."""
    p = Product.query.get(product_id)
    if not p or not p.is_active:
        abort_json(404, "not_found", "Product not found")

    return {
        "id": p.id,
        "sku": p.sku,
        "name": p.name,
        "description": p.description,
        "category": p.category,
        "price_cents": p.price_cents,
        "stock_qty": p.stock_qty,
        "image_url": p.image_url,
    }, 200


# --- Reviews endpoints (match SDD naming) ---
@bp.get("/products/<int:product_id>/get_reviews_star")
def get_reviews_star(product_id: int):
    """GET average star rating."""
    avg_star = db.session.query(func.avg(Review.star)).filter(Review.product_id == product_id, Review.star.isnot(None)).scalar()
    return {"product_id": product_id, "average_star": round(float(avg_star), 2) if avg_star is not None else None}, 200


@bp.get("/products/<int:product_id>/get_reviews_comments")
def get_reviews_comments(product_id: int):
    """GET all customer comments."""
    comments = (
        Review.query.filter_by(product_id=product_id)
        .filter(Review.comment.isnot(None))
        .order_by(Review.created_at.desc())
        .limit(100)
        .all()
    )
    return {
        "product_id": product_id,
        "comments": [{"id": r.id, "account_id": r.account_id, "comment": r.comment, "created_at": r.created_at.isoformat()} for r in comments],
    }, 200


@bp.post("/products/<int:product_id>/post_reviews_star")
@login_required
def post_reviews_star(product_id: int):
    data = get_json()
    require_fields(data, ["star"])
    star = int(data["star"])
    if star < 1 or star > 5:
        abort_json(400, "validation_error", "Star must be between 1 and 5")

    r = Review(product_id=product_id, account_id=session["user_id"], star=star)
    db.session.add(r)
    db.session.commit()
    return {"id": r.id, "product_id": product_id, "star": r.star}, 201


@bp.post("/products/<int:product_id>/post_reviews_comments")
@login_required
def post_reviews_comments(product_id: int):
    data = get_json()
    require_fields(data, ["comment"])
    comment = str(data["comment"]).strip()
    if not comment:
        abort_json(400, "validation_error", "Comment cannot be empty")

    r = Review(product_id=product_id, account_id=session["user_id"], comment=comment)
    db.session.add(r)
    db.session.commit()
    return {"id": r.id, "product_id": product_id, "comment": r.comment}, 201


# Convenience endpoint (optional) used by UI/JMeter: GET and POST in one place
@bp.route("/products/<int:product_id>/reviews", methods=["GET", "POST"])
def reviews(product_id: int):
    if request.method == "GET":
        return get_reviews_comments(product_id)

    # POST
    if not session.get("user_id"):
        abort_json(401, "unauthorized", "Authentication required")

    data = get_json()
    star = data.get("star")
    comment = data.get("comment")
    if star is None and comment is None:
        abort_json(400, "validation_error", "Provide star and/or comment")

    r = Review(product_id=product_id, account_id=session["user_id"], star=int(star) if star is not None else None, comment=comment)
    db.session.add(r)
    db.session.commit()
    return {"id": r.id, "product_id": product_id}, 201
