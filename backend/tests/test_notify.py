import time
from sqlmodel import Session
from app.db import get_engine
from app.models import Zone
from app.services import escalation, notify
from tests.conftest import edge_event, receive_until

HEADERS = {"X-Edge-Token": "test-token"}


def _wait_for(check, timeout: float = 2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = check()
        if result:
            return result
        time.sleep(0.05)
    return check()


def _record_slack(monkeypatch, ok: bool) -> list[str]:
    sent: list[str] = []

    async def fake_send_slack(text: str) -> bool:
        sent.append(text)
        return ok

    monkeypatch.setattr(notify, "send_slack", fake_send_slack)
    monkeypatch.setattr(escalation, "send_slack", fake_send_slack)
    return sent


def test_successful_slack_sets_notified_at_and_broadcasts(client, monkeypatch):
    sent = _record_slack(monkeypatch, ok=True)
    with client.websocket_connect("/ws/events") as ws:
        payload = edge_event()
        ev_id = payload["event_id"]
        assert client.post("/edge/events", json=payload, headers=HEADERS).status_code == 201
        assert ws.receive_json()["type"] == "event.created"

        msg = receive_until(ws, lambda m: m["data"]["notified_at"] is not None)
        assert msg["type"] == "event.updated"
        assert msg["data"]["event_id"] == ev_id

    assert client.get(f"/events/{ev_id}").json()["notified_at"] is not None
    assert len(sent) == 1
    assert ev_id in sent[0]


def test_b13_empty_webhook_keeps_notified_at_null(client):
    payload = edge_event()
    ev_id = payload["event_id"]
    assert client.post("/edge/events", json=payload, headers=HEADERS).status_code == 201

    time.sleep(0.3)
    assert client.get(f"/events/{ev_id}").json()["notified_at"] is None


def test_failed_slack_keeps_notified_at_null(client, monkeypatch):
    sent = _record_slack(monkeypatch, ok=False)
    payload = edge_event()
    ev_id = payload["event_id"]
    client.post("/edge/events", json=payload, headers=HEADERS)

    assert _wait_for(lambda: len(sent) == 1)
    time.sleep(0.1)
    assert client.get(f"/events/{ev_id}").json()["notified_at"] is None


def test_default_template_contains_incident_link(client, monkeypatch):
    sent = _record_slack(monkeypatch, ok=True)
    payload = edge_event()
    ev_id = payload["event_id"]
    client.post("/edge/events", json=payload, headers=HEADERS)

    assert _wait_for(lambda: len(sent) == 1)
    text = sent[0]
    assert text.startswith("[CRITICAL] RESTRICTED_ZONE · stand12 / engine-left · ")
    assert text.endswith(f" · http://localhost:5173/incidents/{ev_id}")


def test_escalation_sends_escalated_text(client, monkeypatch):
    sent = _record_slack(monkeypatch, ok=True)
    with Session(get_engine()) as session:
        zone = session.get(Zone, "engine-left")
        zone.escalate_after_s = 1
        session.add(zone)
        session.commit()

    payload = edge_event()
    ev_id = payload["event_id"]
    client.post("/edge/events", json=payload, headers=HEADERS)

    assert _wait_for(lambda: len(sent) == 2, timeout=3.0)
    assert sent[1].startswith("ESCALADARE · neconfirmat de 1 s · [CRITICAL] RESTRICTED_ZONE")
    assert sent[1].endswith(f"/incidents/{ev_id}")
