import sys
import types
from datetime import date, datetime, timedelta
from sqlmodel import Session
from app.db import get_engine
from app.models import Event
from app.services.kpi import current_shift, shift_window
from app.timeutil import LOCAL_TZ

DAY = "2026-07-15"  # summer: local = UTC+3, morning shift = 03:00-11:00 UTC

_counter = 0


def _event(type: str, severity: str, zone_id: str, status: str, detected_at: datetime, **fields) -> Event:
    global _counter
    _counter += 1
    camera_id = "taxiway-b" if zone_id == "taxiway-b" else "stand12"
    return Event(
        event_id=f"evt_{camera_id}_{1784080000000 + _counter}_{_counter}",
        type=type,
        severity=severity,
        status=status,
        camera_id=camera_id,
        zone_id=zone_id,
        track_id=_counter,
        confidence_detector=0.9,
        confidence_temporal_seen=14,
        confidence_temporal_window=15,
        duration_s=2.0,
        context={"engine_on": False},
        snapshot_url="/snapshots/placeholder.jpg",
        model="person-ppe-v1",
        detected_at=detected_at,
        received_at=detected_at + timedelta(milliseconds=200),
        **fields,
    )


def _seed_morning_shift() -> None:
    t = lambda h, m=0: datetime(2026, 7, 15, h, m)  # noqa: E731 (naive UTC)
    s = timedelta(seconds=1)
    events = [
        _event("RESTRICTED_ZONE", "CRITICAL", "engine-left", "acknowledged", t(4),
               notified_at=t(4) + 1 * s, acked_at=t(4) + 20 * s, acked_by="operator1"),
        _event("NO_PPE", "WARNING", "apron-stand12", "open", t(4, 30), notified_at=t(4, 30) + 2 * s),
        _event("NO_PPE", "WARNING", "apron-stand12", "false_positive", t(5, 10)),
        _event("NO_PPE", "WARNING", "apron-stand12", "acknowledged", t(6),
               notified_at=t(6) + 3 * s, acked_at=t(6) + 10 * s, acked_by="operator1"),
        _event("FOD", "CRITICAL", "taxiway-b", "escalated", t(7),
               notified_at=t(7) + 1.5 * s, escalated_at=t(7) + 30 * s),
        # Outside the window: 05:59 and 14:00 local
        _event("RESTRICTED_ZONE", "CRITICAL", "engine-left", "open", t(2, 59)),
        _event("RESTRICTED_ZONE", "CRITICAL", "engine-left", "open", t(11)),
    ]
    with Session(get_engine()) as session:
        session.add_all(events)
        session.commit()


def test_b12_kpi_numbers(client):
    _seed_morning_shift()

    res = client.get("/kpi", params={"date": DAY, "shift": "morning"})
    assert res.status_code == 200
    assert res.json() == {
        "ppe_compliance": 0.99,
        "open_incidents": 2,
        "avg_detection_to_alert_s": 1.9,
        "escalated": 1,
        # 4 incidente (fals pozitivul nu e incident), 2 confirmate, toate 4 alertate.
        "resolution_rate": 0.5,
        "alerted_incidents": 4,
    }


def test_b12_shift_report_aggregates(client, monkeypatch):
    monkeypatch.setitem(sys.modules, "automation", None)
    _seed_morning_shift()

    res = client.get("/reports", params={"date": DAY, "shift": "morning"})
    assert res.status_code == 200
    data = res.json()
    assert data["shift"] == "morning"
    assert data["date"] == DAY
    assert data["kpi"]["open_incidents"] == 2
    # Fals pozitivul (NO_PPE, 08:10 local) nu e incident: nu apare în by_type,
    # nu apare în by_zone și nu umflă totalul. Se numără separat.
    assert data["by_type"] == [
        {"type": "FOD", "critical": 1, "warning": 0, "false_positive": 0},
        {"type": "NO_PPE", "critical": 0, "warning": 2, "false_positive": 1},
        {"type": "RESTRICTED_ZONE", "critical": 1, "warning": 0, "false_positive": 0},
    ]
    assert data["by_zone"] == [
        {"zone_id": "apron-stand12", "critical": 0, "warning": 2, "avg_ack_s": 10, "false_positive": 1},
        {"zone_id": "engine-left", "critical": 1, "warning": 0, "avg_ack_s": 20, "false_positive": 0},
        {"zone_id": "taxiway-b", "critical": 1, "warning": 0, "avg_ack_s": None, "false_positive": 0},
    ]
    assert data["total_events"] == 4
    assert data["false_positives"] == 1
    # Toate cele 8 ore ale turei, în ordinea turei, inclusiv orele goale.
    assert data["by_hour"] == [
        {"hour": "06", "count": 0},
        {"hour": "07", "count": 2},
        {"hour": "08", "count": 0},
        {"hour": "09", "count": 1},
        {"hour": "10", "count": 1},
        {"hour": "11", "count": 0},
        {"hour": "12", "count": 0},
        {"hour": "13", "count": 0},
    ]
    assert data["summary"] == "Tura de dimineață din 2026-07-15: 4 evenimente, 2 deschise, 1 escaladat."


def test_shift_report_uses_automation_summary(client, monkeypatch):
    received: list[dict] = []

    def summarize(report: dict) -> str:
        received.append(report)
        return "Rezumat generat."

    package = types.ModuleType("automation")
    module = types.ModuleType("automation.report")
    module.summarize = summarize
    package.report = module
    monkeypatch.setitem(sys.modules, "automation", package)
    monkeypatch.setitem(sys.modules, "automation.report", module)

    res = client.get("/reports", params={"date": DAY, "shift": "morning"})
    assert res.json()["summary"] == "Rezumat generat."
    assert "summary" not in received[0]
    assert received[0]["kpi"]["open_incidents"] == 0


def test_empty_shift(client):
    data = client.get("/kpi", params={"date": DAY, "shift": "afternoon"}).json()
    assert data == {
        "ppe_compliance": 1.0,
        "open_incidents": 0,
        "avg_detection_to_alert_s": None,
        "escalated": 0,
        "resolution_rate": None,
        "alerted_incidents": 0,
    }


def test_night_shift_hours_follow_the_shift_not_the_clock(client, monkeypatch):
    monkeypatch.setitem(sys.modules, "automation", None)
    # Tura de noapte 2026-07-15: 19:00 UTC (22:00 local) -> 03:00 UTC (06:00 local).
    t = datetime(2026, 7, 15, 20)  # 23:00 local
    with Session(get_engine()) as session:
        session.add(_event("RESTRICTED_ZONE", "CRITICAL", "engine-left", "open", t))
        session.commit()

    data = client.get("/reports", params={"date": DAY, "shift": "night"}).json()
    assert [row["hour"] for row in data["by_hour"]] == ["22", "23", "00", "01", "02", "03", "04", "05"]
    assert data["by_hour"][1] == {"hour": "23", "count": 1}


def test_shift_of_only_false_positives_has_no_incidents(client, monkeypatch):
    monkeypatch.setitem(sys.modules, "automation", None)
    t = datetime(2026, 7, 15, 12)  # afternoon shift
    with Session(get_engine()) as session:
        session.add_all(
            [
                _event("NO_PPE", "WARNING", "apron-stand12", "false_positive", t),
                _event("NO_PPE", "WARNING", "apron-stand12", "false_positive", t + timedelta(minutes=5)),
            ]
        )
        session.commit()

    data = client.get("/reports", params={"date": DAY, "shift": "afternoon"}).json()
    assert data["total_events"] == 0
    assert data["false_positives"] == 2
    assert data["by_type"] == [{"type": "NO_PPE", "critical": 0, "warning": 0, "false_positive": 2}]
    assert data["kpi"]["resolution_rate"] is None


def test_kpi_requires_both_or_neither(client):
    assert client.get("/kpi", params={"date": DAY}).status_code == 422
    assert client.get("/kpi", params={"shift": "morning"}).status_code == 422
    assert client.get("/kpi").status_code == 200


def test_reports_requires_both(client):
    assert client.get("/reports", params={"date": DAY}).status_code == 422
    assert client.get("/reports", params={"shift": "night", "date": DAY}).status_code == 200


def test_night_shift_window_crosses_midnight():
    start, end = shift_window("night", date(2026, 7, 15))
    assert start == datetime(2026, 7, 15, 19, 0)
    assert end == datetime(2026, 7, 16, 3, 0)


def test_current_shift():
    at = lambda h: datetime(2026, 7, 15, h, 30, tzinfo=LOCAL_TZ)  # noqa: E731
    assert current_shift(at(6)) == ("morning", date(2026, 7, 15))
    assert current_shift(at(14)) == ("afternoon", date(2026, 7, 15))
    assert current_shift(at(23)) == ("night", date(2026, 7, 15))
    assert current_shift(at(3)) == ("night", date(2026, 7, 14))


def test_shift_report_avg_ack_over_all_acked_events(client, monkeypatch):
    monkeypatch.setitem(sys.modules, "automation", None)
    t = datetime(2026, 7, 15, 12)  # afternoon shift: 11:00-19:00 UTC
    s = timedelta(seconds=1)
    acked = {"status": "acknowledged", "acked_by": "operator1"}
    events = [_event("RESTRICTED_ZONE", "CRITICAL", "engine-left", detected_at=t, acked_at=t + 300 * s, **acked)]
    events += [
        _event("NO_PPE", "WARNING", "apron-stand12", detected_at=t + i * s, acked_at=t + (i + 10) * s, **acked)
        for i in range(9)
    ]
    events.append(_event("NO_PPE", "WARNING", "apron-stand12", "open", t))
    with Session(get_engine()) as session:
        session.add_all(events)
        session.commit()

    data = client.get("/reports", params={"date": DAY, "shift": "afternoon"}).json()
    # (300 + 9 * 10) / 10 acks, not the mean of the two zone averages (155)
    assert data["avg_ack_s"] == 39


def test_shift_report_avg_ack_none_without_acks(client, monkeypatch):
    monkeypatch.setitem(sys.modules, "automation", None)
    assert client.get("/reports", params={"date": DAY, "shift": "afternoon"}).json()["avg_ack_s"] is None
