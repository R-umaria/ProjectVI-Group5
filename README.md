# BoxedWithLove (Simple Team Boilerplate)

This is a **simplified** Flask + PostgreSQL + Docker boilerplate for a small university team:
- Easy to navigate (few folders, few files)
- Still meets course constraints: REST JSON API, PostgreSQL DB, Docker container, and routes covering
  **GET, POST, PUT, PATCH, DELETE, OPTIONS**.

## Folder structure (keep it simple)

```
.
├── app.py                 # create app + register API + basic web pages
├── config.py              # environment config
├── db.py                  # SQLAlchemy init
├── models.py              # database tables (ORM models)
├── routes/                # API modules (one file per module)
│   ├── auth.py
│   ├── catalog.py
│   ├── cart.py
│   ├── orders.py
│   └── options.py         # OPTIONS route
├── templates/             # minimal server-rendered UI
├── static/                # minimal CSS/JS
├── tests/                 # smoke test
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Quickstart (Docker)

```bash
cp .env.example .env
docker compose up --build

# In another terminal (first time):
docker compose exec web flask --app app.py init-db
docker compose exec web flask --app app.py seed
```

Open:
- Web UI: http://localhost:8080
- API: http://localhost:8080/api

## Quickstart (Local dev)

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

docker compose up -d db
flask --app app.py init-db
flask --app app.py seed
flask --app app.py run --debug --port=8080
```

## API (minimum)
- `GET /api/products?limit=&offset=` (paged list)
- `GET /api/products/<id>`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/cart`
- `POST /api/cart/items`
- `PUT /api/cart/items/<item_id>` (replace qty)
- `PATCH /api/cart/items/<item_id>` (partial update)
- `DELETE /api/cart/items/<item_id>`
- `POST /api/orders` (checkout)
- `GET /api/orders`
- `OPTIONS /api/options` (course verb requirement)

## Team workflow (recommended)
- Each teammate primarily edits **one** file under `routes/` for their module:
  - Auth: `routes/auth.py`
  - Catalog: `routes/catalog.py`
  - Cart: `routes/cart.py`
  - Orders: `routes/orders.py`
- Shared changes (models, config) should go through PRs.
