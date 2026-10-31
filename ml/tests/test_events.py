from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from safesight_ml.events import EdgeEvent


def make_event(**overrides):
    payload = {
        "event_id": "evt_stand12_1793356933120_17",
        "type": "RESTRICTED_ZONE",
        "severity": "CRITICAL",
        "camera_id": "stand12",
        "zone_id": "engine-left",
        "track_id": 17,
        "confidence": {"detector": 0.91, "temporal": {"seen": 14, "window": 15}},
        "duration_s": 1.4,
        "context": {"engine_on": True},
        "snapshot_url": "/snapshots/evt_stand12_1793356933120_17.jpg",
        "model": "yolo26n.pt",
        "detected_at": datetime(2026, 10, 30, 10, 42, 13, 120000, tzinfo=UTC),
    }
    payload.update(overrides)
    return EdgeEvent(**payload)


def test_event_serializes_contract_fields_only():
    payload = json.loads(make_event().model_dump_json())
    assert payload["event_id"] == "evt_stand12_1793356933120_17"
    assert payload["type"] == "RESTRICTED_ZONE"
    assert payload["confidence"] == {"detector": 0.91, "temporal": {"seen": 14, "window": 15}}
    assert payload["detected_at"] == "2026-10-30T10:42:13.120Z"
    assert "status" not in payload
    assert "report" not in payload
    assert "received_at" not in payload


def test_event_id_format_is_enforced():
    with pytest.raises(ValidationError):
        make_event(event_id="evt_0142")


def test_snapshot_url_rejects_minio():
    with pytest.raises(ValidationError):
        make_event(snapshot_url="minio://safesight/evt_0142.jpg")


def test_snapshot_url_must_be_a_snapshots_path():
    with pytest.raises(ValidationError):
        make_event(snapshot_url="//evil.example/x.jpg")


def test_extra_backend_fields_are_rejected():
    with pytest.raises(ValidationError):
        make_event(status="open")


def test_detected_at_must_be_timezone_aware():
    with pytest.raises(ValidationError):
        make_event(detected_at=datetime(2026, 10, 30, 10, 42, 13))


def test_confidence_must_be_structured():
    with pytest.raises(ValidationError):
        make_event(confidence={"detector": 0.91, "temporal": "14/15 cadre"})


def test_crowd_is_reserved_and_rejected():
    with pytest.raises(ValidationError):
        make_event(type="CROWD")


def test_temporal_window_must_be_positive():
    with pytest.raises(ValidationError):
        make_event(confidence={"detector": 0.91, "temporal": {"seen": 0, "window": 0}})


def test_event_id_requires_thirteen_digit_timestamp():
    with pytest.raises(ValidationError):
        make_event(event_id="evt_stand12_179335693312_17")
