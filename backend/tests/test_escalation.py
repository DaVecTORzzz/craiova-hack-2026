import time
from datetime import timedelta
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.db import get_engine
from app.main import create_app
from app.models import Event, EventAction, Zone
from app.timeutil import utcnow
from tests.conftest import edge_event

HEADERS = {"X-Edge-Token": "test-token"}


def _set_escalate_after(zone_id: str, seconds: int | None) -> None:
    # PUT /zones arrives in step 11; update the row directly until then.
    with Session(get_engine()) as session:
        zone = session.get(Zone, zone_id)
        zone.escalate_after_s = seconds
        session.add(zone)
        session.commit()


def _actions(event_id: str) -> list[str]:
    with Session(get_engine()) as session:
        rows = session.exec(select(EventAction).where(EventAction.event_id == event_id)).all()
        return [r.action for r in rows]


def _create_event(client, **overrides) -> str:
    payload = edge_event(**overrides)
    res = client.post("/edge/events", json=payload, headers=HEADERS)
    assert res.status_code == 201
    return payload["event_id"]


def test_b09_unacked_event_escalates(client):
    _set_escalate_after("engine-left", 1)
    with client.websocket_connect("/ws/events") as ws:
        ev_id = _create_event(client)
        assert ws.receive_json()["type"] == "event.created"

        time.sleep(1.5)

        data = client.get(f"/events/{ev_id}").json()
        assert data["status"] == "escalated"
        assert data["escalated_at"] is not None
        assert _actions(ev_id) == ["escalate"]

        msg = ws.receive_json()
        assert msg["type"] == "event.updated"
        assert msg["data"]["event_id"] == ev_id
        assert msg["data"]["status"] == "escalated"


def test_ack_before_timeout_stops_escalation(client):
    _set_escalate_after("engine-left", 1)
    ev_id = _create_event(client)

    time.sleep(0.3)
    assert client.post(f"/events/{ev_id}/ack", json={"operator": "operator1"}).status_code == 200

    time.sleep(1.2)
    data = client.get(f"/events/{ev_id}").json()
    assert data["status"] == "acknowledged"
    assert data["escalated_at"] is None
    assert _actions(ev_id) == ["ack"]


def test_false_positive_stops_escalation(client):
    _set_escalate_after("engine-left", 1)
    ev_id = _create_event(client)

    client.post(f"/events/{ev_id}/false-positive", json={"operator": "operator1"})

    time.sleep(1.5)
    assert client.get(f"/events/{ev_id}").json()["status"] == "false_positive"


def test_reopen_restarts_timer(client):
    _set_escalate_after("engine-left", 1)
    ev_id = _create_event(client)
    client.post(f"/events/{ev_id}/ack", json={"operator": "operator1"})

    assert client.post(f"/events/{ev_id}/reopen", json={"operator": "operator1"}).status_code == 200

    time.sleep(1.5)
    data = client.get(f"/events/{ev_id}").json()
    assert data["status"] == "escalated"
    assert _actions(ev_id) == ["ack", "reopen", "escalate"]


def test_zone_without_escalation_never_escalates(client):
    _set_escalate_after("engine-left", None)
    ev_id = _create_event(client)

    time.sleep(1.5)
    assert client.get(f"/events/{ev_id}").json()["status"] == "open"


def test_camera_offline_never_escalates(client):
    _set_escalate_after("engine-left", 1)
    ev_id = _create_event(client, type="CAMERA_OFFLINE", severity="WARNING")

    time.sleep(1.5)
    assert client.get(f"/events/{ev_id}").json()["status"] == "open"


def test_recover_timers_escalates_overdue_events(client):
    _set_escalate_after("engine-left", 1)
    overdue = _create_event(client)
    client.post(f"/events/{overdue}/ack", json={"operator": "operator1"})
    with Session(get_engine()) as session:
        event = session.get(Event, overdue)
        event.status = "open"
        event.received_at = utcnow() - timedelta(seconds=5)
        session.add(event)
        session.commit()

    # A restart runs recover_timers() in the lifespan.
    with TestClient(create_app()) as restarted:
        assert restarted.get(f"/events/{overdue}").json()["status"] == "escalated"
