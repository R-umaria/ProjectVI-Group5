# How TEAM should work (no stepping on each other)
## Module ownership mapping

* Ceren (Module 1 — Auth & Accounts): `boxedwithlove/modules/auth/`

* Krishi (Module 2 — Catalog & Product Details): `boxedwithlove/modules/catalog/`

* Andy (Module 3 — Cart Management): `boxedwithlove/modules/cart/`

* Rishi (Module 4 — Checkout & Orders + perf testing): `boxedwithlove/modules/orders/` + `/jmeter`

## Rules to keep the repo consistent

1. Only touch your module folder + shared files only via PR review:

2. Shared files: models.py, docs/API_CONTRACT.md, docs/DECISIONS.md

3. If a module needs a new DB field/table:

* Update models.py
* Run migrations (locally or in Docker)
* Add the change to docs/API_CONTRACT.md

4. Always return errors via the shared error schema (already wired in factory).

## Local + Docker run commands
### Local (fast dev)
```
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# Start DB (recommended):
docker compose up -d db

# Initialize DB migrations (already initialized in repo) then:

flask --app boxedwithlove.wsgi db upgrade
flask --app boxedwithlove.wsgi seed

flask --app boxedwithlove.wsgi run --debug --port=8080
```
```
Docker (performance-test-like)
docker compose up --build
docker compose exec web flask --app boxedwithlove.wsgi db upgrade
docker compose exec web flask --app boxedwithlove.wsgi seed
```

## Notes for performance testing (so you don’t paint yourself into a corner)

These defaults are set up to support your SRS performance narrative (read-heavy browsing + mixed cart/checkout writes) 

SRS_Group05:

* Product list supports pagination (limit, offset) to prevent unbounded responses.
* Models include indexes on the fields you’ll hit in hot paths (email, foreign keys).
* Checkout endpoint uses a single DB transaction to create Order + OrderItems + clear cart (correctness under concurrency).