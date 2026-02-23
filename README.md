
# BoxedWithLove — Project VI (Web + Performance)

BoxedWithLove is a lightweight e-commerce web application for a gift box/basket store. Users can browse products, view product details and reviews, manage a cart (guest or logged-in), save payment methods (non-sensitive), and place orders via a RESTful JSON API.

This project is implemented with **Flask + PostgreSQL + Docker** and is designed to support **iterative performance testing with Apache JMeter** under predictable seasonal traffic spikes (read-heavy browsing + mixed cart/checkout writes).

---

## Team & Modules

- **Ceren** — Auth & Accounts  
- **Krishi** — Catalog & Product Details  
- **Andy** — Cart Management  
- **Rishi** — Checkout & Orders + Performance Testing

---

## Tech Stack

- **Backend:** Python (Flask), SQLAlchemy ORM
- **Database:** PostgreSQL
- **Containerization:** Docker + Docker Compose
- **UI:** Server-rendered Jinja templates + Tailwind-style CSS
- **Testing:** pytest (smoke tests), Apache JMeter (performance)

---

## System Requirements Coverage (Course)

This implementation satisfies the course system constraints, including:
- RESTful API over **HTTP** with **JSON** payloads
- At least one route for each verb: **GET, POST, PUT, PATCH, DELETE, OPTIONS**
- **PostgreSQL** database
- Runs in a **Docker container** during testing

(See course requirements + SRS/SDD for the authoritative requirement mapping.)

---

## Repository Structure

```text
.
├── app.py                 # Flask app, web routes, blueprint registration, CLI commands
├── config.py              # environment config
├── db.py                  # SQLAlchemy init
├── models.py              # ORM models (Users, Products, Cart, Orders, Payment Methods, Reviews, etc.)
├── routes/                # REST API modules (one file per module)
│   ├── auth.py
│   ├── catalog.py
│   ├── cart.py
│   ├── orders.py
│   ├── payment_methods.py
│   └── options.py
├── templates/             # UI pages (Jinja)
├── static/                # CSS/JS/images
├── tests/                 # pytest smoke tests
├── products.csv           # seed data for products
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

---

## Quick Start (Docker - Recommended)

### 1) Configure environment

```
cp .env.example .env
```

### 2) Build and run containers

```bash
docker compose up --build
```

### 3) Initialize DB tables (first run)

In a second terminal:

```bash
docker compose exec web flask --app app.py init-db
```

### 4) Seed products

```bash
docker compose exec web flask --app app.py seed
```

### 5) Open the app

* Web UI: [http://localhost:8080](http://localhost:8080)
* API base: [http://localhost:8080/api](http://localhost:8080/api)

---

## Local Development (Without Docker Web Container)

> You can still run PostgreSQL via Docker and run Flask locally for faster iteration.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env

docker compose up -d db

flask --app app.py init-db
flask --app app.py seed
flask --app app.py run --debug --port=8080
```

---

## API Overview

**Base path:** `/api`
**Auth:** session cookie (set on login)

### Auth & Accounts

* `POST /api/users` — create account
* `POST /api/auth/login` — login (sets session)
* `POST /api/auth/logout` — logout
* `GET  /api/users/me` — get current user

### Catalog & Products

* `GET  /api/products?limit=&offset=&q=&category=&sort=` — list products (paging + filters)
* `GET  /api/products/<id>` — product detail (+ reviews summary + list)
* `POST /api/products/<id>/reviews` — add review (auth required)

### Cart (Guest + Logged-in)

* `GET    /api/cart` — fetch cart + summary totals
* `POST   /api/cart/items` — add item `{ "product_id": int, "quantity": int }`
* `PUT    /api/cart/items/<item_id>` — replace quantity `{ "quantity": int }`
* `PATCH  /api/cart/items/<item_id>` — partial update `{ "quantity": int }`
* `DELETE /api/cart/items/<item_id>` — remove item

> For guest carts, `item_id` is returned like `session_<product_id>`.

### Payment Methods (Non-sensitive)

* `GET    /api/payment-methods` — list payment methods (auth required)
* `POST   /api/payment-methods` — add payment method (auth required)
* `PUT    /api/payment-methods/<id>` — replace payment method
* `PATCH  /api/payment-methods/<id>` — partial update (includes at least one PATCH route)
* `DELETE /api/payment-methods/<id>` — remove payment method
* `OPTIONS /api/payment-methods` and `OPTIONS /api/payment-methods/<id>`

### Orders / Checkout

* `POST   /api/orders` — checkout (cart → order + order items; requires payment method)
* `GET    /api/orders` — list user orders
* `GET    /api/orders/<id>` — order detail (includes items)
* `PATCH  /api/orders/<id>` — limited update (e.g., cancel while `placed`)
* `DELETE /api/orders/<id>` — cancel (soft-cancel via status)
* `OPTIONS /api/orders` and `OPTIONS /api/orders/<id>`

### Global OPTIONS (Course Verb Coverage)

* `OPTIONS /api/options`

---

## Standard Error Response Shape

Errors are returned consistently as:

```json
{
  "error": {
    "code": "validation_error",
    "message": "human readable message"
  }
}
```

---

## Testing (pytest)

Run tests inside Docker:

```bash
docker compose exec -e PYTHONPATH=/app web pytest -q
```

Or locally:

```bash
pytest -q
```

---

## Performance Testing (Apache JMeter)

The load testing narrative targets holiday-season spikes:

* **Browsing rush:** mostly `GET /api/products` and `GET /api/products/<id>`
* **Purchase rush:** `POST /api/cart/items` + `POST /api/orders`

Recommended metrics to report:

* Throughput (req/sec)
* p95 latency
* Error rate

---

## Database & Seeding Notes

* `flask --app app.py init-db` creates tables.
* `flask --app app.py seed` imports product data from `products.csv` (and associates images under `static/images/products/`).

---

## Documentation (Doxygen)

This repository supports Doxygen-generated documentation.

---

## License

Academic project (CSCN73060 / Project VI). All rights reserved to the authors unless otherwise stated.
