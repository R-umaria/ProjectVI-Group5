# BoxedWithLove

BoxedWithLove is a small e-commerce web app for a gift basket / gift box seller. The project is intentionally scoped for CSCN73060 Project 1 to prioritize **performance testing evidence** (baseline → change → re-test → explain).

## Tech stack
- Backend: **Flask (Python)**
- API: RESTful JSON under base path **`/api`**
- Database: **PostgreSQL**
- Containerization: **Docker + docker-compose**
- Performance testing: **Apache JMeter** (holiday-season traffic spike scenarios)

## Repo structure (high-level)
- `boxedwithlove/` — Flask application package
- `boxedwithlove/app/` — app factory, config, extensions, shared utilities, DB models
- `boxedwithlove/modules/` — module-owned routes (Auth, Catalog, Cart, Orders)
- `docs/` — architecture + contribution rules + runbook
- `jmeter/` — JMeter plans and notes for baseline/change/retest

## Module ownership
- **Module 1 — Auth & Accounts:** `boxedwithlove/modules/auth/`
- **Module 2 — Catalog & Product Details:** `boxedwithlove/modules/catalog/`
- **Module 3 — Cart Management:** `boxedwithlove/modules/cart/`
- **Module 4 — Checkout & Orders + Performance Testing:** `boxedwithlove/modules/orders/` + `jmeter/`

## Quickstart (Docker)
```bash
docker compose up --build
# first-time only (in another terminal):
docker compose exec web flask --app boxedwithlove.wsgi db upgrade
docker compose exec web flask --app boxedwithlove.wsgi seed
```

## Quickstart (Local dev + Docker DB)
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

## Documentation
- Architecture overview: `docs/ARCHITECTURE.md`
- Team workflow / rules: `docs/CONTRIBUTING.md`
- Run commands / migrations / seed / JMeter: `docs/RUNBOOK.md`
