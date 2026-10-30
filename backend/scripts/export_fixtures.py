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


def export_fixtures() -> None:
    fixtures_dir = Path(__file__).resolve().parent.parent / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    # 1. Cameras
    cameras = [
        CameraOut(
            id="stand12",
            name="Stand 12 apron",
            rtsp_url="rtsp://localhost:8554/stand12",
            online=True,
            engine_on=False,
        ),
        CameraOut(
            id="taxiway-b",
            name="Taxiway B",
            rtsp_url="rtsp://localhost:8554/taxiway-b",
            online=True,
            engine_on=False,
        ),
        CameraOut(
            id="baggage-area",
            name="Baggage area",
            rtsp_url="rtsp://localhost:8554/baggage-area",
            online=True,
            engine_on=False,
        ),
    ]
    cameras_file = fixtures_dir / "cameras.json"
    cameras_data = [c.model_dump(mode="json") for c in cameras]
    cameras_file.write_text(json.dumps(cameras_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Exported {len(cameras_data)} cameras to {cameras_file}")

    # 2. Zones
    zones = [
        ZoneIO(
            id="engine-left",
            camera_id="stand12",
            name="Motor stâng",
            rule_type=RuleType.RESTRICTED,
            active_when=ActiveWhen.engine_on,
            required_ppe=[],
            severity=Severity.CRITICAL,
            debounce_s=1.0,
            escalate_after_s=30,
            notify_channel="slack",
            polygon=[(0.46, 0.16), (0.76, 0.16), (0.76, 0.68), (0.46, 0.68)],
            reference_frame=None,
        ),
        ZoneIO(
            id="apron-stand12",
            camera_id="stand12",
            name="Platformă Stand 12",
            rule_type=RuleType.PPE_REQUIRED,
            active_when=ActiveWhen.always,
            required_ppe=["hi_vis_vest", "hard_hat", "ear_defenders"],
            severity=Severity.WARNING,
            debounce_s=2.0,
            escalate_after_s=30,
            notify_channel="slack",
            polygon=[(0.04, 0.22), (0.42, 0.22), (0.42, 0.72), (0.04, 0.72)],
            reference_frame=None,
        ),
        ZoneIO(
            id="taxiway-b",
            camera_id="taxiway-b",
            name="Taxiway B",
            rule_type=RuleType.FOD_WATCH,
            active_when=ActiveWhen.always,
            required_ppe=[],
            severity=Severity.CRITICAL,
            debounce_s=3.0,
            escalate_after_s=30,
            notify_channel="slack",
            polygon=[(0.0, 0.76), (1.0, 0.76), (1.0, 0.92), (0.0, 0.92)],
            reference_frame=None,
        ),
        ZoneIO(
            id="baggage-area",
            camera_id="baggage-area",
            name="Zona bagaje",
            rule_type=RuleType.PPE_REQUIRED,
            active_when=ActiveWhen.always,
            required_ppe=["hi_vis_vest"],
            severity=Severity.WARNING,
            debounce_s=2.0,
            escalate_after_s=None,
            notify_channel="slack",
            polygon=[(0.05, 0.10), (0.95, 0.10), (0.95, 0.95), (0.05, 0.95)],
            reference_frame=None,
        ),
    ]
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
        # Example 3: FOD escalated
        EventOut(
            event_id="evt_taxiway-b_1793358000000_0",
            type=EventType.FOD,
            severity=Severity.CRITICAL,
            status=Status.escalated,
            camera_id="taxiway-b",
            zone_id="taxiway-b",
            track_id=0,
            confidence=Confidence(
                detector=0.94,
                temporal=Temporal(seen=15, window=15),
            ),
            duration_s=3.5,
            context=Context(engine_on=False),
            snapshot_url="/snapshots/evt_taxiway-b_1793358000000_0.jpg",
            model="fod-diff-v1",
            detected_at="2026-10-30T11:00:00.000Z",
            received_at="2026-10-30T11:00:00.210Z",
            notified_at="2026-10-30T11:00:01.800Z",
            escalated_at="2026-10-30T11:00:31.800Z",
            acked_at=None,
            acked_by=None,
            report=ReportOut(
                what="Obiect static pe suprafața taxiway-b.",
                where="Camera taxiway-b, zona taxiway-b.",
                when="11:00:00, timp în zonă 3,5 s.",
                severity_reason="Obiectele uitate pot fi aspirate de motoare.",
                recommended_action="Inspectează și îndepărtează obiectul înainte de următoarea mișcare.",
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
