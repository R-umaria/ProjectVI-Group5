# BoxedWithLove (CSCN73060 Project 1)

Flask + PostgreSQL + Docker boilerplate for **BoxedWithLove**.

## Architecture
- Server-rendered UI (Jinja2) + small REST API under `/api`
- Flask app factory + module blueprints (Auth, Catalog, Cart, Orders)
- PostgreSQL persistence via SQLAlchemy + Alembic migrations
- Docker Compose stack for repeatable JMeter performance tests

## Quickstart (local, no Docker)
```bash
python -m venv .venv
source .venv/bin/activate  # (Windows: .venv\\Scripts\\activate)

pip install -r requirements.txt
cp .env.example .env

# Start Postgres (recommended via Docker) OR set DATABASE_URL to your local DB
# Create tables via migrations:
flask --app boxedwithlove.wsgi db upgrade

flask --app boxedwithlove.wsgi run --debug
```

## Quickstart (Docker Compose)
```bash
docker compose up --build

# In another terminal, run migrations:
docker compose exec web flask --app boxedwithlove.wsgi db upgrade
```

## API base path
All endpoints are under: `http://localhost:8080/api/...`

## Error format (standard)
All errors return JSON:
```json
{ "error": { "code": "validation_error", "message": "...", "details": { }, "request_id": "..." } }
```

## Module ownership
- Module 1: Auth & Accounts
- Module 2: Catalog & Products (+ Reviews)
- Module 3: Cart
- Module 4: Checkout & Orders (+ Payment Methods) + Performance Testing
