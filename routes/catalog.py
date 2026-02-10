from flask import Blueprint, request
from sqlalchemy import or_, func

from models import Product, Category, Review
from helpers import error
from config import Config

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
        .order_by(Review.review_date.desc())
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
                "customer_id": r.customer_id,
                "product_id": r.product_id,
                "rating": r.rating,
                "comment": r.comment,
                "review_date": r.review_date.isoformat() if r.review_date else None,
            }
            for r in reviews
        ],
    }, 200