# Runbook

Common commands for local development, Docker execution, migrations, seeding, and performance testing.

## Local dev (recommended: Docker DB)
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

docker compose up -d db
flask --app boxedwithlove.wsgi db upgrade
flask --app boxedwithlove.wsgi seed
flask --app boxedwithlove.wsgi run --debug --port=8080
```

## Docker (web + db)
```bash
docker compose up --build
# first-time only:
docker compose exec web flask --app boxedwithlove.wsgi db upgrade
docker compose exec web flask --app boxedwithlove.wsgi seed
```

## Migrations (if using Flask-Migrate/Alembic)
Create a migration after changing `models.py`:
```bash
flask --app boxedwithlove.wsgi db migrate -m "describe change"
flask --app boxedwithlove.wsgi db upgrade
```

## Seeding
The scaffold includes a `seed` command (if present) to load basic products/users for testing.
```bash
flask --app boxedwithlove.wsgi seed
```

## JMeter workflow (baseline → change → re-test)
1. Baseline run:
   - record p95 latency / throughput / error rate
2. Apply one change (index, pagination, query optimization)
3. Re-run the same test plan
4. Write a short explanation + before/after table in `jmeter/README.md` or a dated markdown file

Suggested scenarios:
- Browsing rush (read-heavy):
  - `GET /api/products` (paged)
  - `GET /api/products/{id}`
- Purchase rush (mixed writes):
  - `POST /api/cart/items`
  - `PATCH /api/cart/items/{id}`
  - `POST /api/orders` (checkout)
