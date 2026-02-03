# BoxedWithLove API Contract

Base path: `/api`

## Common
- **Content-Type**: `application/json`
- **Error schema**:
```json
{ "error": { "code": "string", "message": "string", "details": {}, "request_id": "string" } }
```

## Auth & Accounts (Module 1)
- `POST /users` create account
- `POST /auth/login` login (session)
- `POST /auth/logout` logout
- `GET /users/me` current user

## Catalog & Products + Reviews (Module 2)
- `GET /products` list products (optional `category`, `limit`, `offset`)
- `GET /products/{id}` product details
- `GET /products/{id}/get_reviews_star`
- `GET /products/{id}/get_reviews_comments`
- `POST /products/{id}/post_reviews_star`
- `POST /products/{id}/post_reviews_comments`

## Cart (Module 3)
- `GET /cart`
- `POST /cart/add`
- `PUT /cart/update`
- `DELETE /cart/remove`
- `DELETE /cart/clear`
- `GET /cart/validate`

## Checkout & Orders + Payment Methods (Module 4)
- `GET /payment-methods`
- `POST /payment-methods`
- `PUT /payment-methods/{payment_method_id}`
- `PATCH /payment-methods/{payment_method_id}`
- `DELETE /payment-methods/{payment_method_id}`

- `POST /orders` checkout
- `GET /orders` order history
- `GET /orders/{order_id}` order details
- `PATCH /orders/{order_id}` limited status update
- `DELETE /orders/{order_id}` cancel (soft)

- `OPTIONS /options` (preflight route)
- `OPTIONS /orders` (preflight route)
