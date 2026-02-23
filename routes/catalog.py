from flask import Blueprint, request, session
from sqlalchemy import or_, func

from models import Product, Category, Review
from helpers import error
from config import Config

from db import db
bp = Blueprint("catalog_api", __name__)

@bp.get("/products")
def list_products():
    try:
        limit = int(request.args.get("limit", Config.DEFAULT_LIMIT))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return error("validation_error", "limit/offset must be integers", 400)

    limit = max(1, min(limit, Config.MAX_LIMIT))
    offset = max(0, offset)

    search = (request.args.get("q") or "").strip()
    category = (request.args.get("category") or "").strip()
    sort = (request.args.get("sort") or "popular").strip()

    q = Product.query

    # Search
    if search:
        like = f"%{search}%"
        q = q.filter(
            or_(
                Product.name.ilike(like),
                Product.description.ilike(like),
                Product.sku.ilike(like),
            )
        )

    # Category filter (category passed as NAME like "Basket")
    if category:
        q = q.join(Category).filter(Category.category_name == category)

    # Sort
    if sort == "price_asc":
        q = q.order_by(Product.price_cents.asc())
    elif sort == "price_desc":
        q = q.order_by(Product.price_cents.desc())
    elif sort == "newest":
        q = q.order_by(Product.created_at.desc())
    else:
        # "popular" fallback (you can later replace with real popularity)
        q = q.order_by(Product.id.asc())

    total = q.count()
    items = q.limit(limit).offset(offset).all()

    return {
        "items": [
            {
                "id": p.id,
                "sku": p.sku,
                "name": p.name,
                "description": p.description,
                "price_cents": p.price_cents,
                "image_url": p.image_url,
                "category": p.category.category_name if p.category else None,
                "stock": p.stock,
                "is_available": p.is_available,
            }
            for p in items
        ],
        "paging": {"limit": limit, "offset": offset, "total": total},
    }, 200


@bp.get("/products/<int:product_id>")
def product_detail(product_id: int):
    p = Product.query.get(product_id)
    if not p:
        return error("not_found", "product not found", 404)

    reviews = (
        Review.query
        .filter(Review.product_id == product_id)
        .order_by(Review.created_at.desc(), Review.id.desc())
        .all()
    )

    avg_rating = (
        Review.query.with_entities(func.avg(Review.rating))
        .filter(Review.product_id == product_id)
        .scalar()
    )
    avg_rating = float(avg_rating) if avg_rating is not None else 0.0

    return {
        "id": p.id,
        "sku": p.sku,
        "name": p.name,
        "description": p.description,
        "price_cents": p.price_cents,
        "image_url": p.image_url,
        "stock": p.stock,
        "is_available": p.is_available,
        "category": p.category.category_name if p.category else None,
        "reviews_summary": {
            "avg_rating": avg_rating,
            "count": len(reviews),
        },
        "reviews": [
            {
                "id": r.id,
                "user_id": r.user_id,
                "product_id": r.product_id,
                "rating": r.rating,
                "comment": r.comment,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reviews
        ],
    }, 200

@bp.post("/products/<int:product_id>/reviews")
def add_review(product_id: int):
    if "user_id" not in session:
        return error("unauthorized", "Login required", 401)

    data = request.get_json() or {}
    rating_raw = data.get("rating")
    comment = (data.get("comment") or "").strip() or None

    try:
        rating = int(rating_raw)
    except Exception:
        rating = 0

    if rating < 1 or rating > 5:
        return error("validation_error", "Rating must be between 1 and 5", 400)

    # Ensure product exists
    if not Product.query.get(product_id):
        return error("not_found", "product not found", 404)

    review = Review(
        user_id=session["user_id"],
        product_id=product_id,
        rating=rating,
        comment=comment,
    )

    db.session.add(review)
    db.session.commit()

    return {
        "review": {
            "id": review.id,
            "user_id": review.user_id,
            "product_id": review.product_id,
            "rating": review.rating,
            "comment": review.comment,
            "created_at": review.created_at.isoformat() if review.created_at else None,
        }
    }, 201