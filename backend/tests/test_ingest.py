from sqlmodel import Session

from app.db import get_engine
from app.models import Camera
from tests.conftest import edge_event

HEADERS = {"X-Edge-Token": "test-token"}


def test_b01_ingest_and_visible_in_events(client):
    payload = edge_event()
    ev_id = payload["event_id"]

    # 1. Ingest event
    res = client.post("/edge/events", json=payload, headers=HEADERS)
    assert res.status_code == 201
    data = res.json()
    assert data["event_id"] == ev_id
    assert data["status"] == "open"
    assert data["camera_id"] == payload["camera_id"]
    assert data["zone_id"] == payload["zone_id"]
    assert data["received_at"] is not None
    assert data["report"] is None

    # 2. Visible in GET /events
    list_res = client.get("/events")
    assert list_res.status_code == 200
    events = list_res.json()
    assert any(e["event_id"] == ev_id for e in events)

    # 3. Visible in GET /events/{event_id}
    detail_res = client.get(f"/events/{ev_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["event_id"] == ev_id
    assert detail["type"] == payload["type"]


def test_b02_duplicate_event_id_returns_200(client):
    payload = edge_event()
    ev_id = payload["event_id"]

    # First ingest -> 201
    res1 = client.post("/edge/events", json=payload, headers=HEADERS)
    assert res1.status_code == 201

    # Second ingest of same event_id -> 200
    res2 = client.post("/edge/events", json=payload, headers=HEADERS)
    assert res2.status_code == 200
    assert res2.json()["event_id"] == ev_id

    # Event count in /events should only have 1 of this event_id
    list_res = client.get(f"/events?camera_id={payload['camera_id']}")
    assert list_res.status_code == 200
    matching = [e for e in list_res.json() if e["event_id"] == ev_id]
    assert len(matching) == 1


def test_b03_extra_field_status_via_http_returns_422(client):
    payload = edge_event(status="open")
    res = client.post("/edge/events", json=payload, headers=HEADERS)
    assert res.status_code == 422


def test_b04_invalid_confidence_via_http_returns_422(client):
    # string confidence
    payload1 = edge_event(confidence="14/15")
    res1 = client.post("/edge/events", json=payload1, headers=HEADERS)
    assert res1.status_code == 422

    # simple float confidence
    payload2 = edge_event(confidence=0.9)
    res2 = client.post("/edge/events", json=payload2, headers=HEADERS)
    assert res2.status_code == 422


def test_missing_or_invalid_token_returns_401(client):
    payload = edge_event()

    # Missing token header
    res_missing = client.post("/edge/events", json=payload)
    assert res_missing.status_code == 401
    assert res_missing.json() == {"detail": "invalid edge token"}

    # Invalid token header
    res_wrong = client.post("/edge/events", json=payload, headers={"X-Edge-Token": "wrong-token"})
    assert res_wrong.status_code == 401
    assert res_wrong.json() == {"detail": "invalid edge token"}


def test_unknown_camera_returns_404(client):
    payload = edge_event(camera_id="unknown-camera")
    res = client.post("/edge/events", json=payload, headers=HEADERS)
    assert res.status_code == 404
    assert res.json() == {"detail": "unknown camera_id"}


def test_unknown_zone_returns_404(client):
    payload = edge_event(zone_id="unknown-zone", type="RESTRICTED_ZONE")
    res = client.post("/edge/events", json=payload, headers=HEADERS)
    assert res.status_code == 404
    assert res.json() == {"detail": "unknown zone_id"}


def test_zone_from_another_camera_returns_422(client):
    payload = edge_event(camera_id="stand12", zone_id="taxiway-b")
    res = client.post("/edge/events", json=payload, headers=HEADERS)
    assert res.status_code == 422
    assert res.json() == {"detail": "zone does not belong to camera"}


def test_camera_offline_with_unknown_zone_returns_201_and_sets_camera_offline(client):
    payload = edge_event(
        type="CAMERA_OFFLINE",
        camera_id="stand12",
        zone_id="arbitrary-zone",
        track_id=0,
    )
    res = client.post("/edge/events", json=payload, headers=HEADERS)
    assert res.status_code == 201

    with Session(get_engine()) as session:
        camera = session.get(Camera, "stand12")
        assert camera is not None
        assert camera.online is False

    # Normal event brings camera back online
    normal_payload = edge_event(
        type="RESTRICTED_ZONE",
        camera_id="stand12",
        zone_id="engine-left",
    )
    res2 = client.post("/edge/events", json=normal_payload, headers=HEADERS)
    assert res2.status_code == 201

    with Session(get_engine()) as session:
        camera = session.get(Camera, "stand12")
        assert camera is not None
        assert camera.online is True


def test_get_events_filters_and_404(client):
    # Test filters: status, severity, camera_id
    payload1 = edge_event(severity="CRITICAL", camera_id="stand12", zone_id="engine-left")
    payload2 = edge_event(severity="WARNING", camera_id="stand12", zone_id="apron-stand12", type="NO_PPE")

    client.post("/edge/events", json=payload1, headers=HEADERS)
    client.post("/edge/events", json=payload2, headers=HEADERS)

    # Filter by severity
    res_crit = client.get("/events?severity=CRITICAL")
    assert res_crit.status_code == 200
    assert all(e["severity"] == "CRITICAL" for e in res_crit.json())

    # Filter by camera_id
    res_cam = client.get("/events?camera_id=stand12")
    assert res_cam.status_code == 200
    assert all(e["camera_id"] == "stand12" for e in res_cam.json())

    # Unknown event detail 404
    res_404 = client.get("/events/evt_nonexistent_1234567890123_1")
    assert res_404.status_code == 404
    assert res_404.json() == {"detail": "event not found"}
