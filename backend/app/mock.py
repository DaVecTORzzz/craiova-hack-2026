import asyncio
import logging
import random
import time
from datetime import datetime, timezone
from sqlmodel import Session

from app.config import get_settings
from app.db import get_engine
from app.models import Camera
from app.schemas import Confidence, Context, EdgeEventIn, EventType, Severity, Temporal
from app.services.events import ingest

logger = logging.getLogger("safesight.mock")

TEMPLATES = [
    {
        "type": EventType.RESTRICTED_ZONE,
        "severity": Severity.CRITICAL,
        "camera_id": "stand12",
        "zone_id": "engine-left",
        "model": "person-ppe-v1",
    },
    {
        "type": EventType.NO_PPE,
        "severity": Severity.WARNING,
        "camera_id": "stand12",
        "zone_id": "apron-stand12",
        "model": "person-ppe-v1",
    },
    {
        "type": EventType.FOD,
        "severity": Severity.CRITICAL,
        "camera_id": "taxiway-b",
        "zone_id": "taxiway-b",
        "model": "fod-diff-v1",
    },
]


async def run_mock_generator() -> None:
    settings = get_settings()
    logger.info(f"Mock generator started (interval={settings.mock_interval_s}s)")
    engine = get_engine()

    try:
        while True:
            await asyncio.sleep(settings.mock_interval_s)
            tpl = random.choice(TEMPLATES)
            track_id = 0 if tpl["type"] == EventType.FOD else random.randint(1, 99)
            unix_ms = int(time.time() * 1000)
            camera_id = tpl["camera_id"]
            event_id = f"evt_{camera_id}_{unix_ms}_{track_id}"
            now = datetime.now(timezone.utc)

            with Session(engine) as session:
                camera = session.get(Camera, camera_id)
                engine_on = camera.engine_on if camera is not None else False

                event_in = EdgeEventIn(
                    event_id=event_id,
                    type=tpl["type"],
                    severity=tpl["severity"],
                    camera_id=camera_id,
                    zone_id=tpl["zone_id"],
                    track_id=track_id,
                    confidence=Confidence(
                        detector=round(random.uniform(0.7, 0.95), 2),
                        temporal=Temporal(seen=random.randint(12, 15), window=15),
                    ),
                    duration_s=round(random.uniform(1.0, 4.0), 1),
                    context=Context(engine_on=engine_on),
                    snapshot_url="/snapshots/placeholder.jpg",
                    model=tpl["model"],
                    detected_at=now,
                )

                try:
                    await ingest(session, event_in)
                except Exception as e:
                    logger.error(f"Mock generator failed to ingest: {e}")
    except asyncio.CancelledError:
        logger.info("Mock generator stopped")
