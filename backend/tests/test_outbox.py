"""Outbox: o alertă nu se pierde la un timeout, un 429 sau un restart.

Contractul cu restul aplicației: `ingest()` scrie un rând `pending` în
`notification_outbox`; worker-ul îl trimite, iar `notified_at` se setează o
singură dată, la primul succes real.
"""

import time

from sqlmodel import Session, select

from app.config import get_settings
from app.db import get_engine
from app.models import NotificationOutbox
from app.services import notify, outbox
from tests.conftest import edge_event

HEADERS = {"X-Edge-Token": "test-token"}


def _wait_for(check, timeout: float = 4.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = check()
        if result:
            return result
        time.sleep(0.05)
    return check()


def _rows() -> list[NotificationOutbox]:
    with Session(get_engine()) as session:
        return list(session.exec(select(NotificationOutbox)).all())


def _record(monkeypatch, results: list[bool]) -> list[str]:
    """Fake Slack that answers from `results` (last value repeats); records texts."""
    sent: list[str] = []
    answers = list(results)

    async def fake_send_slack(text: str) -> bool:
        sent.append(text)
        return answers.pop(0) if len(answers) > 1 else answers[0]

    monkeypatch.setattr(notify, "send_slack", fake_send_slack)
    return sent


def _fast_backoff(monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "outbox_backoff_s", "0.05")
    monkeypatch.setattr(get_settings(), "outbox_interval_s", 0.05)


def test_ingest_enqueues_one_rendered_message(client, monkeypatch):
    _fast_backoff(monkeypatch)
    sent = _record(monkeypatch, [True])
    payload = edge_event()

    assert client.post("/edge/events", json=payload, headers=HEADERS).status_code == 201
    # The DB row is the truth: the fake sender runs before the row is marked sent.
    assert _wait_for(lambda: _rows() and _rows()[0].status == "sent")
    assert len(sent) == 1

    rows = _rows()
    assert len(rows) == 1
    row = rows[0]
    assert (row.event_id, row.kind, row.channel) == (payload["event_id"], "new", "slack")
    assert row.status == "sent"
    assert row.attempts == 1
    assert row.sent_at is not None
    # Textul e randat la enqueue: retry-ul nu poate spune altă oră.
    assert payload["event_id"] in row.text
    assert row.text == sent[0]
    assert client.get(f"/events/{payload['event_id']}").json()["notified_at"] is not None


def test_failed_send_retries_with_the_same_text(client, monkeypatch):
    _fast_backoff(monkeypatch)
    # A configured webhook is what makes a failure retryable; without one the
    # outbox gives up on the first try (test_without_webhook_...).
    monkeypatch.setattr(get_settings(), "slack_webhook_url", "https://hooks.example.invalid/x")
    sent = _record(monkeypatch, [False, True])
    payload = edge_event()

    client.post("/edge/events", json=payload, headers=HEADERS)
    assert _wait_for(lambda: _rows() and _rows()[0].status == "sent")

    row = _rows()[0]
    assert row.attempts == 2
    assert len(sent) == 2
    assert sent[0] == sent[1]
    assert client.get(f"/events/{payload['event_id']}").json()["notified_at"] is not None


def test_enqueue_is_idempotent_per_event_and_kind(client, monkeypatch):
    _record(monkeypatch, [True])
    assert outbox.enqueue("evt_stand12_1793356933120_17", "new", "primul") is True
    assert outbox.enqueue("evt_stand12_1793356933120_17", "new", "al doilea") is False

    rows = [row for row in _rows() if row.event_id == "evt_stand12_1793356933120_17"]
    assert len(rows) == 1
    assert rows[0].text == "primul"


def test_without_webhook_it_fails_once_and_does_not_retry(client, monkeypatch):
    _fast_backoff(monkeypatch)
    # conftest lasă SLACK_WEBHOOK_URL gol: nu există unde trimite.
    payload = edge_event()
    client.post("/edge/events", json=payload, headers=HEADERS)

    assert _wait_for(lambda: _rows() and _rows()[0].status == "failed")
    time.sleep(0.3)

    row = _rows()[0]
    assert row.attempts == 1
    assert row.last_error == "no webhook configured"
    assert client.get(f"/events/{payload['event_id']}").json()["notified_at"] is None


def test_exhausted_attempts_are_marked_failed_and_visible_in_health(client, monkeypatch):
    _fast_backoff(monkeypatch)
    monkeypatch.setattr(get_settings(), "slack_webhook_url", "https://hooks.example.invalid/x")
    monkeypatch.setattr(get_settings(), "outbox_max_attempts", 2)
    sent = _record(monkeypatch, [False])

    payload = edge_event()
    client.post("/edge/events", json=payload, headers=HEADERS)

    assert _wait_for(lambda: _rows() and _rows()[0].status == "failed")
    assert _rows()[0].attempts == 2
    assert len(sent) == 2

    stats = client.get("/health").json()["notifications"]
    assert stats["failed_24h"] >= 1
    assert stats["pending"] == 0


def test_replay_heals_a_notification_row_lost_before_commit(client):
    """Eventul și alerta se commit împreună; dacă rândul lipsește, un replay al edge-ului îl reface."""
    payload = edge_event()
    assert client.post("/edge/events", json=payload, headers=HEADERS).status_code == 201

    with Session(get_engine()) as session:
        row = session.exec(
            select(NotificationOutbox).where(NotificationOutbox.event_id == payload["event_id"])
        ).first()
        assert row is not None
        session.delete(row)
        session.commit()

    # Același event_id: ingestia e idempotentă, dar alerta lipsă e re-creată.
    assert client.post("/edge/events", json=payload, headers=HEADERS).status_code == 200

    with Session(get_engine()) as session:
        rows = session.exec(
            select(NotificationOutbox).where(NotificationOutbox.event_id == payload["event_id"])
        ).all()
    assert len(rows) == 1


def test_pending_rows_are_picked_up_after_a_restart(client, monkeypatch):
    """Un rând rămas `pending` (proces mort înainte de trimitere) pleacă la următorul drain."""
    _record(monkeypatch, [True])
    event_id = "evt_stand12_1793356933999_9"
    outbox.enqueue(event_id, "new", "mesaj vechi")

    assert _wait_for(lambda: _rows() and _rows()[0].status == "sent")
    assert _rows()[0].event_id == event_id
