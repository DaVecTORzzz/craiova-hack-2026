import pytest
from pydantic import ValidationError
from sqlmodel import Session, select

from app.db import get_engine
from app.models import Camera, ConfigState, Zone
from app.schemas import EdgeEventIn, ZoneIO
from tests.conftest import edge_event


def test_valid_payload_passes():
    payload = edge_event()
    event_in = EdgeEventIn.model_validate(payload)
    assert event_in.event_id == payload["event_id"]
    assert event_in.camera_id == "stand12"
    assert event_in.zone_id == "engine-left"


def test_b03_extra_field_status_fails():
    # B-03: payload with "status": "open" fails validation
    payload = edge_event(status="open")
    with pytest.raises(ValidationError) as exc_info:
        EdgeEventIn.model_validate(payload)
    errors = exc_info.value.errors()
    assert any("status" in str(err["loc"]) for err in errors)


def test_b04_confidence_invalid_types_fail():
    # B-04: confidence as "14/15" and as 0.9 both fail
    payload_str = edge_event(confidence="14/15")
    with pytest.raises(ValidationError):
        EdgeEventIn.model_validate(payload_str)

    payload_float = edge_event(confidence=0.9)
    with pytest.raises(ValidationError):
        EdgeEventIn.model_validate(payload_float)


def test_snapshot_url_rejects_minio_and_bad_root():
    for bad in ("minio://safesight/evt.jpg", "//evil.example/evt.jpg", "snapshots/evt.jpg"):
        payload = edge_event(snapshot_url=bad)
        with pytest.raises(ValidationError):
            EdgeEventIn.model_validate(payload)


def test_snapshot_url_accepts_contract_urls():
    for good in ("/snapshots/evt.jpg", "http://localhost:8000/snapshots/evt.jpg"):
        payload = edge_event(snapshot_url=good)
        assert EdgeEventIn.model_validate(payload).snapshot_url == good


def test_polygon_out_of_bounds_coordinate_fails():
    # polygon with a coordinate 1.2 fails
    zone_data = {
        "id": "engine-left",
        "camera_id": "stand12",
        "name": "Motor stâng",
        "rule_type": "RESTRICTED",
        "active_when": "engine_on",
        "required_ppe": [],
        "severity": "CRITICAL",
        "debounce_s": 1.0,
        "escalate_after_s": 30,
        "notify_channel": "slack",
        "polygon": [[0.46, 1.2], [0.76, 0.16], [0.76, 0.68]],
        "reference_frame": None,
    }
    with pytest.raises(ValidationError) as exc_info:
        ZoneIO.model_validate(zone_data)
    assert "polygon coordinates must be normalized 0-1" in str(exc_info.value)


def test_valid_zone_io_passes():
    zone_data = {
        "id": "engine-left",
        "camera_id": "stand12",
        "name": "Motor stâng",
        "rule_type": "RESTRICTED",
        "active_when": "engine_on",
        "required_ppe": [],
        "severity": "CRITICAL",
        "debounce_s": 1.0,
        "escalate_after_s": 30,
        "notify_channel": "slack",
        "polygon": [[0.46, 0.16], [0.76, 0.16], [0.76, 0.68]],
        "reference_frame": None,
    }
    zone = ZoneIO.model_validate(zone_data)
    assert zone.id == "engine-left"


def test_db_has_seed_cameras_and_zones_after_startup(client):
    # Startup lifespan runs seed(), verify 3 cameras and 4 zones
    with Session(get_engine()) as session:
        cameras = session.exec(select(Camera)).all()
        assert len(cameras) == 3
        camera_ids = {c.id for c in cameras}
        assert camera_ids == {"stand12", "taxiway-b", "baggage-area"}

        zones = session.exec(select(Zone)).all()
        assert len(zones) == 4
        zone_ids = {z.id for z in zones}
        assert zone_ids == {"engine-left", "apron-stand12", "taxiway-b", "baggage-area"}

        config = session.get(ConfigState, 1)
        assert config is not None
        assert config.config_version == 1
