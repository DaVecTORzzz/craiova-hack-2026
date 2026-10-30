from __future__ import annotations

from datetime import UTC, datetime

import httpx
import numpy as np

from safesight_ml.events import EdgeEvent
from safesight_ml.sink import HttpSink


def make_event() -> EdgeEvent:
    return EdgeEvent(
        event_id="evt_stand12_1793356933120_17",
        type="RESTRICTED_ZONE",
        severity="CRITICAL",
        camera_id="stand12",
        zone_id="engine-left",
        track_id=17,
        confidence={"detector": 0.91, "temporal": {"seen": 14, "window": 15}},
        duration_s=1.4,
        context={"engine_on": True},
        snapshot_url="/snapshots/x.jpg",
        model="yolo26n.pt",
        detected_at=datetime(2026, 10, 30, 10, 42, 13, 120000, tzinfo=UTC),
    )


def test_http_sink_posts_snapshot_then_event_with_edge_token():
    calls: list[tuple[str, str, str | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path, request.headers.get("X-Edge-Token")))
        if request.url.path == "/edge/snapshots":
            return httpx.Response(200, json={"snapshot_url": "/snapshots/x.jpg"})
        if request.url.path == "/edge/events":
            return httpx.Response(201, json={"ok": True})
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    sink = HttpSink("http://backend", "test-token", client=client)

    url = sink.store_snapshot("evt_stand12_1793356933120_17", np.zeros((10, 10, 3), dtype=np.uint8))
    assert url == "/snapshots/x.jpg"

    sink.emit(make_event())
    assert [call[1] for call in calls] == ["/edge/snapshots", "/edge/events"]
    assert all(call[2] == "test-token" for call in calls)
