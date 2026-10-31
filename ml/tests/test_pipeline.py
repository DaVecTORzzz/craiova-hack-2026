from __future__ import annotations

import json

import numpy as np

from safesight_ml.detector import Detection, FakeDetector
from safesight_ml.pipeline import Pipeline
from safesight_ml.run import _metrics_source, _resolve_fps
from safesight_ml.run import main as run_main
from safesight_ml.sink import JsonlSink
from safesight_ml.zones import Zone

ZONE = Zone(
    id="engine-left",
    camera_id="stand12",
    name="Motor stâng",
    rule_type="RESTRICTED",
    active_when="engine_on",
    severity="CRITICAL",
    debounce_s=1.0,
    escalate_after_s=30,
    polygon=[(0.46, 0.16), (0.76, 0.16), (0.76, 0.68), (0.46, 0.68)],
)


class RecordingBlurrer:
    def __init__(self) -> None:
        self.calls = 0
        self.boxes: list[tuple[float, float, float, float]] = []

    def blur(self, frame: np.ndarray, boxes=()) -> np.ndarray:
        self.calls += 1
        self.boxes.extend(boxes)
        return frame


class RecordingSink:
    def __init__(self) -> None:
        self.events = []
        self.snapshots = []

    def store_snapshot(self, event_id: str, frame: np.ndarray) -> str:
        self.snapshots.append(event_id)
        return f"/snapshots/{event_id}.jpg"

    def emit(self, event) -> None:
        self.events.append(event)


def test_pipeline_emits_one_contract_event_and_blurs_once():
    frames = [
        [Detection(track_id=1, bbox=(0.50, 0.20, 0.60, 0.60), confidence=0.91)]
        for _ in range(20)
    ]
    blurrer = RecordingBlurrer()
    sink = RecordingSink()
    pipeline = Pipeline(
        camera_id="stand12",
        zones=[ZONE],
        detector=FakeDetector(frames),
        blurrer=blurrer,
        sink=sink,
        engine_on=True,
        start_epoch=1_793_356_933.0,
    )

    emitted = []
    for step in range(20):
        emitted.extend(pipeline.process(np.zeros((360, 640, 3), dtype=np.uint8), now_s=step / 10))

    assert len(emitted) == 1
    event = emitted[0]
    assert event.type == "RESTRICTED_ZONE"
    assert event.severity == "CRITICAL"
    assert event.zone_id == "engine-left"
    assert event.track_id == 1
    assert event.snapshot_url == f"/snapshots/{event.event_id}.jpg"
    assert event.model == "fake-person-v1"
    assert event.confidence.temporal.seen >= 5
    assert event.context.engine_on is True
    assert "status" not in event.model_dump()
    assert blurrer.calls == 1
    assert blurrer.boxes == [(0.50, 0.20, 0.60, 0.60)]
    assert sink.snapshots == [event.event_id]


def test_pipeline_uses_clock_for_detected_at():
    frames = [
        [Detection(track_id=1, bbox=(0.50, 0.20, 0.60, 0.60), confidence=0.91)]
        for _ in range(20)
    ]
    sink = RecordingSink()
    pipeline = Pipeline(
        camera_id="stand12",
        zones=[ZONE],
        detector=FakeDetector(frames),
        blurrer=RecordingBlurrer(),
        sink=sink,
        engine_on=True,
        start_epoch=1_793_356_933.0,
        clock=lambda: 1_793_356_999.0,
    )
    for step in range(20):
        pipeline.process(np.zeros((360, 640, 3), dtype=np.uint8), now_s=step / 10)

    assert sink.events[0].detected_at.timestamp() == 1_793_356_999.0


def test_pipeline_respects_engine_off():
    frames = [
        [Detection(track_id=1, bbox=(0.50, 0.20, 0.60, 0.60), confidence=0.91)]
        for _ in range(20)
    ]
    sink = RecordingSink()
    pipeline = Pipeline(
        camera_id="stand12",
        zones=[ZONE],
        detector=FakeDetector(frames),
        blurrer=RecordingBlurrer(),
        sink=sink,
        engine_on=False,
        start_epoch=1_793_356_933.0,
    )
    for step in range(20):
        pipeline.process(np.zeros((360, 640, 3), dtype=np.uint8), now_s=step / 10)
    assert sink.events == []


def test_jsonl_sink_writes_event_and_snapshot(tmp_path):
    frames = [
        [Detection(track_id=1, bbox=(0.50, 0.20, 0.60, 0.60), confidence=0.91)]
        for _ in range(20)
    ]
    sink = JsonlSink(tmp_path)
    pipeline = Pipeline(
        camera_id="stand12",
        zones=[ZONE],
        detector=FakeDetector(frames),
        blurrer=RecordingBlurrer(),
        sink=sink,
        engine_on=True,
        start_epoch=1_793_356_933.0,
    )
    for step in range(20):
        pipeline.process(np.zeros((360, 640, 3), dtype=np.uint8), now_s=step / 10)

    lines = (tmp_path / "events.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["type"] == "RESTRICTED_ZONE"
    assert (tmp_path / "snapshots" / f"{payload['event_id']}.jpg").is_file()


def test_fps_resolution_handles_nan_and_zero():
    assert _resolve_fps(0.0, float("nan")) == 25.0
    assert _resolve_fps(0.0, 0.0) == 25.0
    assert _resolve_fps(0.0, 30.0) == 30.0
    assert _resolve_fps(15.0, 30.0) == 15.0


def test_fake_cli_runs_end_to_end(tmp_path):
    code = run_main(
        [
            "--fake",
            "--engine-on",
            "--dry-run",
            "--out",
            str(tmp_path),
            "--max-frames",
            "30",
        ]
    )
    assert code == 0
    lines = (tmp_path / "events.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["type"] == "RESTRICTED_ZONE"


def test_cli_writes_run_metrics(tmp_path):
    metrics_path = tmp_path / "reports" / "run.json"

    code = run_main(
        [
            "--fake",
            "--engine-on",
            "--dry-run",
            "--out",
            str(tmp_path / "out"),
            "--max-frames",
            "30",
            "--metrics-json",
            str(metrics_path),
        ]
    )

    assert code == 0
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert metrics["source"] == "fake"
    assert metrics["frames"] == 30
    assert metrics["events"] == 1
    assert metrics["event_types"] == {"RESTRICTED_ZONE": 1}
    assert metrics["event_details"][0]["track_id"] == 1
    assert metrics["event_details"][0]["zone_id"] == "engine-left"
    assert metrics["fps"] > 0
    assert metrics["model"] == "synthetic-person-v1"
    assert metrics["max_frames"] == 30
    assert metrics["duration_s"] == 0
    assert metrics["dropped_frames"] == 0
    assert metrics["stages"]["detect"]["calls"] == 30
    assert metrics["stages"]["snapshot"]["calls"] == 1
    assert metrics["stages"]["detect"]["mean_ms"] >= 0


def test_metrics_source_redacts_rtsp_credentials():
    assert _metrics_source("rtsp://user:secret@cam.local:8554/stand12?token=abc") == "rtsp://cam.local:8554/stand12"
    assert _metrics_source("clip.mp4") == "clip.mp4"
    assert _metrics_source(None) == "fake"


def test_pipeline_skips_events_while_emit_events_is_off():
    frames = [[Detection(track_id=1, bbox=(0.50, 0.20, 0.60, 0.60), confidence=0.91)] for _ in range(20)]
    sink = RecordingSink()
    pipeline = Pipeline(
        camera_id="stand12",
        zones=[ZONE],
        detector=FakeDetector(frames),
        blurrer=RecordingBlurrer(),
        sink=sink,
        engine_on=True,
    )
    pipeline.emit_events = False
    blank = np.zeros((360, 640, 3), dtype=np.uint8)
    for step in range(20):
        assert pipeline.process(blank, now_s=step / 10) == []
    assert sink.events == [] and sink.snapshots == []

    pipeline.emit_events = True
    emitted = [event for step in range(20, 40) for event in pipeline.process(blank, now_s=step / 10)]
    assert len(emitted) == 1
