# JMeter assets

Recommended test plan structure (aligns with SRS performance intent):

1. **Browsing Rush** (read-heavy)
   - 80% `GET /api/products`
   - 20% `GET /api/products/{id}`

2. **Purchase Rush** (mixed)
   - `POST /api/auth/login`
   - `POST /api/cart/add` + `PUT /api/cart/update`
   - `POST /api/payment-methods`
   - `POST /api/orders`

Track: p95 latency, throughput, error-rate. Keep results in `jmeter/results/...` with baseline vs iteration numbers.
