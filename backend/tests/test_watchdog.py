"""Watchdog: o cameră care tace devine incident, iar revenirea o rezolvă singură."""

import asyncio
from datetime import timedelta

from sqlmodel import Session, select

from app.config import get_settings
from app.db import get_engine
from app.models import Camera, CameraOutage, EdgeHeartbeat, Event, EventAction, NotificationOutbox
from app.services import watchdog
from app.timeutil import utcnow

HEADERS = {"X-Edge-Token": "test-token"}


def _age_beat(camera_id: str, seconds: int) -> None:
    with Session(get_engine()) as session:
        beat = session.get(EdgeHeartbeat, camera_id)
        beat.last_seen_at = utcnow() - timedelta(seconds=seconds)
        session.add(beat)
        session.commit()


def _offline_events(camera_id: str) -> list[Event]:
    with Session(get_engine()) as session:
        return list(
            session.exec(
                select(Event)
                .where(Event.type == "CAMERA_OFFLINE")
                .where(Event.camera_id == camera_id)
                .order_by(Event.detected_at)
            ).all()
        )


def _outages(camera_id: str) -> list[CameraOutage]:
    with Session(get_engine()) as session:
        return list(session.exec(select(CameraOutage).where(CameraOutage.camera_id == camera_id)).all())


def _beat(camera_id: str) -> EdgeHeartbeat:
    with Session(get_engine()) as session:
        return session.get(EdgeHeartbeat, camera_id)


def _tick() -> list[str]:
    return asyncio.run(watchdog.tick())


def test_a_camera_that_just_reported_is_not_offline(client):
    _age_beat("stand12", 30)
    assert _tick() == []
    assert _offline_events("stand12") == []


def test_silence_opens_exactly_one_incident(client):
    _age_beat("stand12", 120)

    assert _tick() == ["stand12"]
    events = _offline_events("stand12")
    assert len(events) == 1
    event = events[0]
    assert event.status == "open"
    assert event.severity == "WARNING"
    assert event.track_id == 0
    assert event.zone_id == "stand12"
    assert event.snapshot_url == "/snapshots/placeholder.jpg"
    assert event.model == "watchdog-v1"

    with Session(get_engine()) as session:
        assert session.get(Camera, "stand12").online is False
    assert len(_outages("stand12")) == 1
    assert _outages("stand12")[0].ended_at is None
    assert _beat("stand12").outage_event_id == event.event_id

    # Still silent on the next tick: no second incident, and no second alert.
    assert _tick() == []
    assert len(_offline_events("stand12")) == 1


def test_a_heartbeat_resolves_the_incident_and_closes_the_outage(client):
    _age_beat("stand12", 120)
    _tick()
    event_id = _offline_events("stand12")[0].event_id

    res = client.post("/edge/heartbeat", json={"camera_id": "stand12"}, headers=HEADERS)
    assert res.status_code == 200
    assert res.json() == {"ok": True, "online": True}

    with Session(get_engine()) as session:
        event = session.get(Event, event_id)
        assert event.status == "resolved"
        assert session.get(Camera, "stand12").online is True
        actions = session.exec(select(EventAction).where(EventAction.event_id == event_id)).all()
        assert [action.action for action in actions] == ["recovered"]
        notifications = session.exec(
            select(NotificationOutbox).where(NotificationOutbox.event_id == event_id)
        ).all()
        assert {row.kind for row in notifications} == {"new", "recovery"}

    assert _outages("stand12")[0].ended_at is not None
    assert _beat("stand12").outage_event_id is None


def test_a_second_outage_is_a_new_incident(client):
    _age_beat("stand12", 120)
    _tick()
    client.post("/edge/heartbeat", json={"camera_id": "stand12"}, headers=HEADERS)

    _age_beat("stand12", 120)
    _tick()

    events = _offline_events("stand12")
    assert len(events) == 2
    assert events[0].event_id != events[1].event_id
    assert len(_outages("stand12")) == 2


def test_the_watchdog_can_be_switched_off(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "camera_offline_after_s", 0)
    _age_beat("stand12", 10_000)
    assert _tick() == []
    assert _offline_events("stand12") == []


def test_heartbeat_requires_the_edge_token(client):
    assert client.post("/edge/heartbeat", json={"camera_id": "stand12"}).status_code == 401


def test_heartbeat_for_an_unknown_camera_is_404(client):
    res = client.post("/edge/heartbeat", json={"camera_id": "nope"}, headers=HEADERS)
    assert res.status_code == 404


def test_polling_for_zones_counts_as_a_heartbeat(client):
    _age_beat("stand12", 120)
    before = _beat("stand12").last_seen_at

    res = client.get("/edge/zones", params={"camera_id": "stand12"}, headers=HEADERS)
    assert res.status_code == 200

    assert _beat("stand12").last_seen_at > before
    assert _tick() == []
    assert _offline_events("stand12") == []


def test_mock_mode_does_not_invent_offline_cameras(client, monkeypatch):
    """Mock = niciun edge pornit; tăcerea e starea normală, nu un incident."""
    monkeypatch.setattr(get_settings(), "use_mock", True)
    _age_beat("stand12", 10_000)
    assert _tick() == []
    assert _offline_events("stand12") == []
