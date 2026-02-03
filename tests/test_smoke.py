from boxedwithlove.app.factory import create_app


def test_health():
    app = create_app()
    with app.test_client() as c:
        r = c.get("/health")
        assert r.status_code == 200
        assert r.json["status"] == "ok"


def test_api_index():
    app = create_app()
    with app.test_client() as c:
        r = c.get("/api")
        assert r.status_code == 200
        assert "endpoints" in r.json
