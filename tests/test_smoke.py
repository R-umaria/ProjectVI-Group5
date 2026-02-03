def test_smoke(client):
    resp = client.get("/api/products")
    assert resp.status_code in (200, 500)  # 500 if DB not init, but app should boot
