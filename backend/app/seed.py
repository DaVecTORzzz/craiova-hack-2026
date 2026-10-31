from datetime import UTC, timedelta
from pathlib import Path

from PIL import Image
from sqlmodel import Session, select

from app.config import get_settings
from app.models import Camera, ConfigState, Event, Zone
from app.timeutil import utcnow


def ensure_placeholder_image(snapshot_dir: str) -> None:
    path = Path(snapshot_dir) / "placeholder.jpg"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (640, 360), color="#3A3A3A")
        img.save(path, format="JPEG")


def seed_cameras(session: Session) -> None:
    now = utcnow()
    cameras = [
        Camera(
            id="stand12",
            name="Stand 12 apron",
            rtsp_url="rtsp://localhost:8554/stand12",
            engine_on=False,
            online=True,
            updated_at=now,
        ),
        Camera(
            id="taxiway-b",
            name="Taxiway B",
            rtsp_url="rtsp://localhost:8554/taxiway-b",
            engine_on=False,
            online=True,
            updated_at=now,
        ),
        Camera(
            id="baggage-area",
            name="Baggage area",
            rtsp_url="rtsp://localhost:8554/baggage-area",
            engine_on=False,
            online=True,
            updated_at=now,
        ),
    ]
    for cam in cameras:
        if session.get(Camera, cam.id) is None:
            session.add(cam)


def seed_zones(session: Session) -> None:
    zones = [
        Zone(
            id="engine-left",
            camera_id="stand12",
            name="Motor stâng",
            rule_type="RESTRICTED",
            active_when="engine_on",
            required_ppe=[],
            severity="CRITICAL",
            debounce_s=1.0,
            escalate_after_s=30,
            notify_channel="slack",
            polygon=[[0.46, 0.16], [0.76, 0.16], [0.76, 0.68], [0.46, 0.68]],
            reference_frame=None,
        ),
        Zone(
            id="apron-stand12",
            camera_id="stand12",
            name="Platformă Stand 12",
            rule_type="PPE_REQUIRED",
            active_when="always",
            required_ppe=["hi_vis_vest", "hard_hat", "ear_defenders"],
            severity="WARNING",
            debounce_s=2.0,
            escalate_after_s=30,
            notify_channel="slack",
            polygon=[[0.04, 0.22], [0.42, 0.22], [0.42, 0.72], [0.04, 0.72]],
            reference_frame=None,
        ),
        Zone(
            id="taxiway-b",
            camera_id="taxiway-b",
            name="Taxiway B",
            rule_type="FOD_WATCH",
            active_when="always",
            required_ppe=[],
            severity="CRITICAL",
            debounce_s=3.0,
            escalate_after_s=30,
            notify_channel="slack",
            polygon=[[0.0, 0.76], [1.0, 0.76], [1.0, 0.92], [0.0, 0.92]],
            reference_frame=None,
        ),
        Zone(
            id="baggage-area",
            camera_id="baggage-area",
            name="Zona bagaje",
            rule_type="PPE_REQUIRED",
            active_when="always",
            required_ppe=["hi_vis_vest"],
            severity="WARNING",
            debounce_s=2.0,
            escalate_after_s=None,
            notify_channel="slack",
            polygon=[[0.05, 0.10], [0.95, 0.10], [0.95, 0.95], [0.05, 0.95]],
            reference_frame=None,
        ),
    ]
    for zone in zones:
        if session.get(Zone, zone.id) is None:
            session.add(zone)


def seed_config_state(session: Session) -> None:
    if session.get(ConfigState, 1) is None:
        session.add(ConfigState(id=1, config_version=1))


def seed_demo_events_if_requested(session: Session) -> None:
    settings = get_settings()
    if not settings.seed_demo_events:
        return
    if session.exec(select(Event)).first() is not None:
        return

    now = utcnow()
    templates = [
        ("RESTRICTED_ZONE", "CRITICAL", "stand12", "engine-left", "acknowledged"),
        ("NO_PPE", "WARNING", "stand12", "apron-stand12", "open"),
        ("FOD", "CRITICAL", "taxiway-b", "taxiway-b", "escalated"),
        ("NO_PPE", "WARNING", "baggage-area", "baggage-area", "false_positive"),
    ]

    for i in range(12):
        ev_type, sev, cam, zn, st = templates[i % len(templates)]
        detected = now - timedelta(minutes=(12 - i) * 15)
        received = detected + timedelta(milliseconds=200)
        notified = received + timedelta(seconds=1.5)
        acked = (notified + timedelta(seconds=10)) if st in ("acknowledged", "false_positive") else None
        escalated = (notified + timedelta(seconds=35)) if st == "escalated" else None
        track_id = 0 if ev_type in ("FOD", "CAMERA_OFFLINE") else (i + 1)

        event = Event(
            event_id=f"evt_{cam}_{int(detected.replace(tzinfo=UTC).timestamp() * 1000)}_{track_id}",
            type=ev_type,
            severity=sev,
            status=st,
            camera_id=cam,
            zone_id=zn,
            track_id=track_id,
            confidence_detector=0.92,
            confidence_temporal_seen=14,
            confidence_temporal_window=15,
            duration_s=2.5,
            context={"engine_on": (ev_type == "RESTRICTED_ZONE")},
            snapshot_url="/snapshots/placeholder.jpg",
            model="fod-diff-v1" if ev_type == "FOD" else "person-ppe-v1",
            detected_at=detected,
            received_at=received,
            notified_at=notified,
            escalated_at=escalated,
            acked_at=acked,
            acked_by="Ana" if acked else None,
        )
        session.add(event)


def seed(session: Session) -> None:
    settings = get_settings()
    ensure_placeholder_image(settings.snapshot_dir)
    seed_cameras(session)
    seed_zones(session)
    seed_config_state(session)
    seed_demo_events_if_requested(session)
    session.commit()
