# Contributing

This repository is organized so each teammate can work mostly in their module folder with minimal merge conflicts.

## Branching
- Create feature branches from `main`
- Suggested names:
  - `feature/auth-login`
  - `feature/catalog-pagination`
  - `feature/cart-patch-qty`
  - `feature/orders-checkout`

## Ownership boundaries (default rule)
Only edit your module folder unless the change is explicitly coordinated:

- Auth & Accounts: `boxedwithlove/modules/auth/`
- Catalog & Product Details: `boxedwithlove/modules/catalog/`
- Cart Management: `boxedwithlove/modules/cart/`
- Checkout & Orders: `boxedwithlove/modules/orders/` and `jmeter/`

Shared files (edit via PR + review):
- `boxedwithlove/app/models.py` (DB schema)
- endpoint contract docs (e.g., `docs/API_CONTRACT.md` if present)
- `docs/DECISIONS.md` (naming/versioning decisions)

## API rules (consistency)
- Base path: `/api`
- RESTful JSON request/response
- Use the standard error schema from `app/common/errors.py`
- Return correct HTTP status codes:
  - 200/201 success
  - 400 validation
  - 401 unauthenticated
  - 403 unauthorized
  - 404 not found
  - 409 conflict (optional)
  - 500 server error (unexpected)

## Database rules
- Any schema change must include:
  1) model change in `models.py`
  2) migration (if migrations are enabled)
  3) a note in contract docs (fields, constraints, status codes)
- Add indexes for fields used in hot queries (email lookups, foreign keys, common filters).

## Performance discipline (course requirement alignment)
For any meaningful change that might affect performance:
- Document baseline vs after metrics:
  - p95 latency
  - throughput (req/s)
  - error rate
- Put JMeter artifacts/notes under `jmeter/`
- Avoid increasing response payload sizes without pagination or clear need.

## PR checklist
Before requesting review:
- App starts locally and/or in Docker
- Migrations run cleanly (if applicable)
- No endpoints return inconsistent error shapes
- If endpoints changed: docs updated (contract + runbook if needed)
- Optional but recommended: add/adjust a smoke test for the endpoint
