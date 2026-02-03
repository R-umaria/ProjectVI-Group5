from flask import Blueprint, request

from models import Product
from app import error
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

    q = Product.query.order_by(Product.id.asc())
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
            } for p in items
        ],
        "paging": {"limit": limit, "offset": offset, "total": total},
    }, 200

@bp.get("/products/<int:product_id>")
def product_detail(product_id: int):
    p = Product.query.get(product_id)
    if not p:
        return error("not_found", "product not found", 404)
    return {
        "id": p.id,
        "sku": p.sku,
        "name": p.name,
        "description": p.description,
        "price_cents": p.price_cents,
        "image_url": p.image_url,
    }, 200
