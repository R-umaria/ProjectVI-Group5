# Architecture

This document explains the “infrastructure” files in the Flask scaffold and how requests flow through the app.

## Request / boot flow (what happens when the app starts)

### 1) WSGI entrypoint
Production servers (e.g., Gunicorn) import:

- `boxedwithlove.wsgi:app`

This file exposes a single variable named `app`, created by the app factory.

### 2) App factory
`boxedwithlove/app/factory.py` contains `create_app(...)` which:

1. Loads configuration (`app/config.py`)
2. Initializes extensions (`app/extensions.py`) — e.g., SQLAlchemy, Migrate
3. Registers API blueprints (module routes) under `/api`
4. Registers error handlers (shared JSON error schema)
5. Adds common middleware (request IDs, timing, logging hooks if enabled)

This pattern is industry-standard because it supports:
- clean separation of configuration per environment (dev/test/prod)
- easy testing (each test can create a fresh app instance)
- reduced circular imports

## Key folders and files

### `boxedwithlove/wsgi.py` (WSGI entrypoint)
**Purpose:** Expose `app` to WSGI servers (Gunicorn) and the `flask --app` CLI.

**When to edit:** Almost never.

---

### `boxedwithlove/app/factory.py` (app factory)
**Purpose:** Create and configure the Flask app instance.

**Typical responsibilities:**
- load config
- initialize DB extensions
- register blueprints
- register error handlers

**When to edit:**
- Adding a new blueprint/module
- Adding global middleware (CORS, request IDs, structured logging)

---

### `boxedwithlove/app/config.py` (configuration)
**Purpose:** Central configuration (DB URL, secret key, environment flags, pagination defaults).

**When to edit:**
- Adding new config variables
- Tuning DB pool settings (useful for performance tests)

---

### `boxedwithlove/app/extensions.py` (Flask extensions)
**Purpose:** Create extension singletons (e.g., `db = SQLAlchemy()`), then initialize them in the factory.

**Why this exists:** Avoids circular imports and keeps initialization consistent.

**When to edit:**
- Adding a new extension (cache, limiter, etc.)

---

### `boxedwithlove/app/models.py` (database models)
**Purpose:** SQLAlchemy ORM models defining tables, columns, relationships, and indexes.

**When to edit:**
- Adding/changing DB entities or fields
- Adding indexes to improve query performance in hot paths

---

### `boxedwithlove/app/api/register.py` (API registration)
**Purpose:** Central registration of module blueprints under `/api`.

**When to edit:**
- Adding a new module blueprint

---

## Shared utilities (`boxedwithlove/app/common/`)

### `errors.py` (standard error schema)
**Purpose:** A single consistent JSON error schema and error handlers.

**Recommended error shape:**
```json
{
  "error": {
    "code": "validation_error",
    "message": "Email is required",
    "details": { "field": "email" }
  }
}
```

Why it matters:
- front-end can handle errors consistently
- JMeter assertions and error-rate calculations stay stable

---

### `auth.py` (auth helpers)
**Purpose:** Shared helpers like `login_required`, `current_user()`, and role/ownership checks.

---

### `validation.py` (input validation helpers)
**Purpose:** Shared parsing/validation for JSON payloads and query parameters (pagination, required fields, types).

---

## Module routes (`boxedwithlove/modules/<module>/routes.py`)

Each module should implement endpoints within its own folder.

- Auth: `modules/auth/routes.py`
- Catalog: `modules/catalog/routes.py`
- Cart: `modules/cart/routes.py`
- Orders: `modules/orders/routes.py`

**Rule of thumb:** Teammates primarily modify their module folder to reduce merge conflicts.

## Performance considerations (design intent)
- Prefer pagination for list endpoints
- Add indexes for fields used in hot queries
- Keep checkout/order placement within a single DB transaction for correctness under concurrency
- Avoid N+1 ORM query patterns (use eager loading when needed)
