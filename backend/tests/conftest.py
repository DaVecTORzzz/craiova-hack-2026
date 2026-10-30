import time
from datetime import datetime, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import reset_engine
from app.main import create_app

_event_counter = 0


def edge_event(**overrides) -> dict:
    global _event_counter
    _event_counter += 1
    # 13 digits ms timestamp
    ms = int(time.time() * 1000)
    event_id = f"evt_stand12_{ms}_{_event_counter}"
    now_iso = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    data = {
        "event_id": event_id,
        "type": "RESTRICTED_ZONE",
        "severity": "CRITICAL",
        "camera_id": "stand12",
        "zone_id": "engine-left",
        "track_id": 17,
        "confidence": {
            "detector": 0.91,
            "temporal": {"seen": 14, "window": 15},
        },
        "duration_s": 1.4,
        "context": {"engine_on": True},
        "snapshot_url": f"/snapshots/{event_id}.jpg",
        "model": "person-ppe-v1",
        "detected_at": now_iso,
    }
    data.update(overrides)
    return data


@pytest.fixture
def make_edge_event():
    return edge_event


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "test.db"
    snapshot_dir = tmp_path / "snapshots"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("SNAPSHOT_DIR", str(snapshot_dir))
    monkeypatch.setenv("EDGE_TOKEN", "test-token")
    monkeypatch.setenv("USE_MOCK", "false")
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "")

    get_settings.cache_clear()
    reset_engine()

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client

    get_settings.cache_clear()
    reset_engine()


def receive_until(ws, predicate, max_messages: int = 10) -> dict:
    """Next WS message matching predicate; skips background updates (report, Slack)."""
    for _ in range(max_messages):
        msg = ws.receive_json()
        if predicate(msg):
            return msg
    raise AssertionError("no matching WebSocket message")


def wait_for_report(client, event_id: str, timeout: float = 2.0) -> dict:
    """Wait until the background report is stored, so it does not race later WS assertions."""
    deadline = time.monotonic() + timeout
    while True:
        data = client.get(f"/events/{event_id}").json()
        if data["report"] is not None or time.monotonic() > deadline:
            return data
        time.sleep(0.05)
