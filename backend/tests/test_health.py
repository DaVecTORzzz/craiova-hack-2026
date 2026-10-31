from unittest.mock import patch


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert data["db"] is True
    assert "edge_last_seen_s" in data
    assert "mock" in data


def test_health_db_failure(client):
    with patch("app.routers.health.check_db", return_value=False):
        response = client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["db"] is False
