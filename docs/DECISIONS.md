# BoxedWithLove Decision Log

## D-001 API base path
- All REST endpoints are prefixed with `/api`.

## D-002 Authentication
- Session-based auth using Flask signed cookies for course scope (no JWT).
- `session['user_id']` is the authenticated principal.

## D-003 Standard error JSON
All error responses:
```json
{ "error": { "code": "...", "message": "...", "details": {}, "request_id": "..." } }
```

## D-004 Module layout
- Each module is a Python package under `boxedwithlove/modules/<module>`.
- Each module exposes a Flask `Blueprint` in `routes.py`.

## D-005 Docker
- Docker Compose provides `web` and `db` services for repeatable performance tests.
