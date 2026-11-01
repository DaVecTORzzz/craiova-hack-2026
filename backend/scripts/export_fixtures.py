import json
import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.schemas import (
    ActiveWhen,
    CameraOut,
    Confidence,
    Context,
    EventOut,
    EventType,
    ReportOut,
    RuleType,
    Severity,
    Status,
    Temporal,
    ZoneIO,
)
from app.routers.zones import zone_io
from app.seed import seed_cameras, seed_zones


class _CollectingSession:
    """Minimal session so the seed can run without a database."""

    def __init__(self) -> None:
        self.added: list = []

    def get(self, _model, _id):
        return None

    def add(self, obj) -> None:
        self.added.append(obj)


def seeded_cameras() -> list[CameraOut]:
    """The cameras exactly as app/seed.py defines them."""
    session = _CollectingSession()
    seed_cameras(session)
    return [
        CameraOut(
            id=camera.id,
            name=camera.name,
            rtsp_url=camera.rtsp_url,
            online=camera.online,
            engine_on=camera.engine_on,
        )
        for camera in session.added
    ]


def seeded_zones() -> list[ZoneIO]:
    """The zones exactly as app/seed.py defines them."""
    session = _CollectingSession()
    seed_zones(session)
    return [zone_io(zone) for zone in session.added]


def export_fixtures() -> None:
    fixtures_dir = Path(__file__).resolve().parent.parent / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    # 1. Cameras — din seed, nu copiate aici. Aceeași listă duplicată ca la zone;
    # la camere încă nu derivase, dar nimic nu o împiedica.
    cameras = seeded_cameras()
    cameras_file = fixtures_dir / "cameras.json"
    cameras_data = [c.model_dump(mode="json") for c in cameras]
    cameras_file.write_text(json.dumps(cameras_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Exported {len(cameras_data)} cameras to {cameras_file}")

    # 2. Zones — built from the seed, never hand-written here. The fixture used to
    # duplicate this list, and the copy drifted from app/seed.py: the demo edge and the
    # UI then disagreed about the same zone (name, debounce, even the polygon).
    zones = seeded_zones()
    zones_file = fixtures_dir / "zones.json"
    zones_data = [z.model_dump(mode="json") for z in zones]
    zones_file.write_text(json.dumps(zones_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Exported {len(zones_data)} zones to {zones_file}")

    # 3. Events
    events = [
        # Example 1: Restricted zone (matching contract example)
        EventOut(
            event_id="evt_stand12_1793356933120_17",
            type=EventType.RESTRICTED_ZONE,
            severity=Severity.CRITICAL,
            status=Status.open,
            camera_id="stand12",
            zone_id="engine-left",
            track_id=17,
            confidence=Confidence(
                detector=0.91,
                temporal=Temporal(seen=14, window=15),
            ),
            duration_s=1.4,
            context=Context(engine_on=True),
            snapshot_url="/snapshots/evt_stand12_1793356933120_17.jpg",
            model="person-ppe-v1",
            detected_at="2026-10-30T10:42:13.120Z",
            received_at="2026-10-30T10:42:13.310Z",
            notified_at="2026-10-30T10:42:14.920Z",
            escalated_at=None,
            acked_at=None,
            acked_by=None,
            report=ReportOut(
                what="Persoană în zona motorului stâng, cu motorul pornit.",
                where="Stand 12, zona engine-left.",
                when="10:42:13, timp în zonă 1,4 s.",
                severity_reason="Motorul e pornit; risc de ingestie sau jet blast.",
                recommended_action="Oprește activitatea la Stand 12. Contactează persoana prin radio.",
                source="llm",
            ),
        ),
        # Example 2: NO_PPE acknowledged
        EventOut(
            event_id="evt_stand12_1793357120000_18",
            type=EventType.NO_PPE,
            severity=Severity.WARNING,
            status=Status.acknowledged,
            camera_id="stand12",
            zone_id="apron-stand12",
            track_id=18,
            confidence=Confidence(
                detector=0.88,
                temporal=Temporal(seen=13, window=15),
            ),
            duration_s=2.1,
            context=Context(engine_on=False),
            snapshot_url="/snapshots/evt_stand12_1793357120000_18.jpg",
            model="person-ppe-v1",
            detected_at="2026-10-30T10:45:20.000Z",
            received_at="2026-10-30T10:45:20.180Z",
            notified_at="2026-10-30T10:45:21.500Z",
            escalated_at=None,
            acked_at="2026-10-30T10:45:35.000Z",
            acked_by="Ana",
            report=ReportOut(
                what="Persoană fără vestă reflectorizantă în zona platformei.",
                where="Stand 12, zona apron-stand12.",
                when="10:45:20, timp în zonă 2,1 s.",
                severity_reason="Lucru pe platformă fără echipamentul complet de protecție.",
                recommended_action="Supervizorul verifică echipamentul persoanei înainte de reluarea lucrului.",
                source="llm",
            ),
        ),
        # Example 3: restricted zone escalated (nobody acknowledged in time)
        EventOut(
            event_id="evt_stand12_1793358000000_23",
            type=EventType.RESTRICTED_ZONE,
            severity=Severity.CRITICAL,
            status=Status.escalated,
            camera_id="stand12",
            zone_id="engine-left",
            track_id=23,
            confidence=Confidence(
                detector=0.89,
                temporal=Temporal(seen=13, window=15),
            ),
            duration_s=2.2,
            context=Context(engine_on=True),
            snapshot_url="/snapshots/evt_stand12_1793358000000_23.jpg",
            model="person-ppe-v1",
            detected_at="2026-10-30T11:00:00.000Z",
            received_at="2026-10-30T11:00:00.210Z",
            notified_at="2026-10-30T11:00:01.800Z",
            escalated_at="2026-10-30T11:00:31.800Z",
            acked_at=None,
            acked_by=None,
            report=ReportOut(
                what="Persoană în zona engine-left.",
                where="Camera stand12, zona engine-left.",
                when="11:00:00, timp în zonă 2,2 s.",
                severity_reason="Zonă restricționată activă; risc de accident.",
                recommended_action="Oprește activitatea în zonă și contactează persoana prin radio.",
                source="template",
            ),
        ),
    ]
    events_file = fixtures_dir / "events.json"
    events_data = [e.model_dump(mode="json") for e in events]
    events_file.write_text(json.dumps(events_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Exported {len(events_data)} events to {events_file}")


if __name__ == "__main__":
    export_fixtures()
