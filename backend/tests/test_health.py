from fastapi.testclient import TestClient

from app.main import create_app


def test_health():
    app = create_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert data["db"] is True
    assert "edge_last_seen_s" in data
    assert "mock" in data
