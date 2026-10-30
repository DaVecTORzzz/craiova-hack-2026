from sqlmodel import Session, select
from app.db import get_engine
from app.models import Event, EventAction
from tests.conftest import edge_event

HEADERS = {"X-Edge-Token": "test-token"}


def _create_event(client) -> str:
    payload = edge_event()
    res = client.post("/edge/events", json=payload, headers=HEADERS)
    assert res.status_code == 201
    return payload["event_id"]


def _actions(event_id: str) -> list[EventAction]:
    with Session(get_engine()) as session:
        return list(session.exec(select(EventAction).where(EventAction.event_id == event_id)).all())


def _set_status(event_id: str, status: str) -> None:
    with Session(get_engine()) as session:
        event = session.get(Event, event_id)
        event.status = status
        session.add(event)
        session.commit()


def test_b06_ack_open_event(client):
    ev_id = _create_event(client)

    res = client.post(f"/events/{ev_id}/ack", json={"operator": "operator1"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "acknowledged"
    assert data["acked_by"] == "operator1"
    assert data["acked_at"] is not None

    rows = _actions(ev_id)
    assert len(rows) == 1
    assert rows[0].action == "ack"
    assert rows[0].operator == "operator1"


def test_ack_escalated_event(client):
    ev_id = _create_event(client)
    _set_status(ev_id, "escalated")

    res = client.post(f"/events/{ev_id}/ack", json={"operator": "operator1"})
    assert res.status_code == 200
    assert res.json()["status"] == "acknowledged"


def test_b07_false_positive_stores_note(client):
    ev_id = _create_event(client)

    res = client.post(f"/events/{ev_id}/false-positive", json={"operator": "operator1", "note": "reflexie"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "false_positive"
    assert data["acked_at"] is None
    assert data["acked_by"] is None

    rows = _actions(ev_id)
    assert len(rows) == 1
    assert rows[0].action == "false_positive"
    assert rows[0].note == "reflexie"


def test_false_positive_after_ack(client):
    ev_id = _create_event(client)
    client.post(f"/events/{ev_id}/ack", json={"operator": "operator1"})

    res = client.post(f"/events/{ev_id}/false-positive", json={"operator": "operator1"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "false_positive"
    # false-positive changes no fields besides status
    assert data["acked_by"] == "operator1"


def test_b08_reopen_after_ack(client):
    ev_id = _create_event(client)
    client.post(f"/events/{ev_id}/ack", json={"operator": "operator1"})

    res = client.post(f"/events/{ev_id}/reopen", json={"operator": "operator2"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "open"
    assert data["acked_at"] is None
    assert data["acked_by"] is None
    assert data["escalated_at"] is None

    rows = _actions(ev_id)
    assert [r.action for r in rows] == ["ack", "reopen"]
    assert rows[1].operator == "operator2"


def test_reopen_allowed_statuses(client):
    for status in ("false_positive", "escalated", "resolved"):
        ev_id = _create_event(client)
        _set_status(ev_id, status)
        res = client.post(f"/events/{ev_id}/reopen", json={"operator": "operator1"})
        assert res.status_code == 200, status
        assert res.json()["status"] == "open"


def test_ack_twice_returns_409(client):
    ev_id = _create_event(client)
    assert client.post(f"/events/{ev_id}/ack", json={"operator": "operator1"}).status_code == 200

    res = client.post(f"/events/{ev_id}/ack", json={"operator": "operator1"})
    assert res.status_code == 409
    assert res.json() == {"detail": "cannot ack an event with status acknowledged"}
    assert len(_actions(ev_id)) == 1


def test_disallowed_transitions_return_409(client):
    ev_id = _create_event(client)

    res = client.post(f"/events/{ev_id}/reopen", json={"operator": "operator1"})
    assert res.status_code == 409
    assert res.json() == {"detail": "cannot reopen an event with status open"}

    client.post(f"/events/{ev_id}/false-positive", json={"operator": "operator1"})
    assert client.post(f"/events/{ev_id}/ack", json={"operator": "operator1"}).status_code == 409
    assert client.post(f"/events/{ev_id}/false-positive", json={"operator": "operator1"}).status_code == 409

    _set_status(ev_id, "resolved")
    assert client.post(f"/events/{ev_id}/ack", json={"operator": "operator1"}).status_code == 409
    assert client.post(f"/events/{ev_id}/false-positive", json={"operator": "operator1"}).status_code == 409


def test_unknown_event_returns_404(client):
    for path in ("ack", "false-positive", "reopen"):
        res = client.post(f"/events/evt_stand12_0000000000000_1/{path}", json={"operator": "operator1"})
        assert res.status_code == 404, path


def test_missing_operator_returns_422(client):
    ev_id = _create_event(client)
    for path in ("ack", "false-positive", "reopen"):
        res = client.post(f"/events/{ev_id}/{path}", json={"note": "x"})
        assert res.status_code == 422, path
    assert _actions(ev_id) == []


def test_actions_broadcast_event_updated(client):
    ev_id = _create_event(client)
    with client.websocket_connect("/ws/events") as ws:
        for path, expected in (("ack", "acknowledged"), ("reopen", "open"), ("false-positive", "false_positive")):
            res = client.post(f"/events/{ev_id}/{path}", json={"operator": "operator1"})
            assert res.status_code == 200
            msg = ws.receive_json()
            assert msg["type"] == "event.updated"
            assert msg["data"]["event_id"] == ev_id
            assert msg["data"]["status"] == expected
