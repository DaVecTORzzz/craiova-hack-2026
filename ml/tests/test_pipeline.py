from __future__ import annotations

import json

import numpy as np

from safesight_ml.detector import Detection, FakeDetector
from safesight_ml import pipeline as pipeline_module
from safesight_ml.pipeline import Pipeline, triggers_event
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


# --- PPE_REQUIRED -> NO_PPE -------------------------------------------------

# Feet at y=0.70 land inside this polygon; the station is generous so the entry
# margin never decides the test.
PPE_ZONE = Zone(
    id="apron-stand12",
    camera_id="stand12",
    name="Apron stand 12",
    rule_type="PPE_REQUIRED",
    active_when="always",
    required_ppe=["hi_vis_vest"],
    severity="WARNING",
    debounce_s=0.5,
    escalate_after_s=30,
    polygon=[(0.40, 0.10), (0.80, 0.10), (0.80, 0.90), (0.40, 0.90)],
)

# 180 px tall at 360 px, above the threshold below which "no vest" is not claimed.
TALL_PERSON = (0.50, 0.20, 0.60, 0.70)
# 144 px tall: enough to see the torso, too small to call a violation.
SMALL_PERSON = (0.50, 0.20, 0.60, 0.60)


def frame_with_vest() -> np.ndarray:
    """Black frame with a fluorescent torso for the tall person box."""
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    # Torso band that ppe.hivis_ratio samples for TALL_PERSON.
    frame[99:171, 332:371] = (0, 255, 0)  # yellow-green in BGR
    return frame


def _run_ppe(
    zone: Zone,
    frame: np.ndarray,
    bbox: tuple[float, float, float, float],
    frames: int = 30,
    engine_on: bool = False,
):
    detections = [[Detection(track_id=1, bbox=bbox, confidence=0.91)] for _ in range(frames)]
    sink = RecordingSink()
    pipeline = Pipeline(
        camera_id="stand12",
        zones=[zone],
        detector=FakeDetector(detections),
        blurrer=RecordingBlurrer(),
        sink=sink,
        engine_on=engine_on,
        start_epoch=1_793_356_933.0,
    )
    for step in range(frames):
        pipeline.process(frame, now_s=step / 10)
    return sink.events


def test_ppe_zone_raises_no_ppe_when_the_vest_is_missing():
    events = _run_ppe(PPE_ZONE, np.zeros((360, 640, 3), dtype=np.uint8), TALL_PERSON)

    assert len(events) == 1
    assert events[0].type == "NO_PPE"
    # Severity comes from the zone, not from the detector.
    assert events[0].severity == "WARNING"
    assert events[0].zone_id == "apron-stand12"
    assert events[0].track_id == 1
    # The engine is irrelevant for a PPE zone that is always active.
    assert events[0].context.engine_on is False


def test_ppe_zone_is_silent_when_the_vest_is_present():
    assert _run_ppe(PPE_ZONE, frame_with_vest(), TALL_PERSON) == []


def test_ppe_zone_is_silent_when_the_person_is_too_small_to_judge():
    # A small person stays "unknown": a low colour score is not proof of a missing vest.
    assert _run_ppe(PPE_ZONE, np.zeros((360, 640, 3), dtype=np.uint8), SMALL_PERSON) == []


def test_ppe_zone_without_hi_vis_requirement_is_silent():
    # Hard hats have no detector yet, so such a zone can never prove a violation.
    hats_only = PPE_ZONE.model_copy(update={"required_ppe": ["hard_hat"]})
    assert _run_ppe(hats_only, np.zeros((360, 640, 3), dtype=np.uint8), TALL_PERSON) == []


def test_restricted_zone_still_fires_for_anyone_inside():
    # Regression: the PPE gate must not leak into other rule types.
    assert len(_run_ppe(ZONE, frame_with_vest(), SMALL_PERSON, engine_on=True)) == 1


# --- triggers_event: the policy, unit by unit --------------------------------


def test_triggers_event_fires_for_anyone_in_a_restricted_zone():
    for state in ("vest", "no_vest", "unknown", None):
        assert triggers_event(ZONE, state) is True


def test_triggers_event_fires_only_on_a_proven_vest_violation():
    assert triggers_event(PPE_ZONE, "no_vest") is True
    assert triggers_event(PPE_ZONE, "vest") is False
    # "unknown" is not proof: small or partly hidden people stay silent.
    assert triggers_event(PPE_ZONE, "unknown") is False
    assert triggers_event(PPE_ZONE, None) is False


def test_triggers_event_ignores_ppe_we_cannot_check():
    hats_only = PPE_ZONE.model_copy(update={"required_ppe": ["hard_hat"]})
    # No detector for hard hats, so no state can ever satisfy this.
    assert triggers_event(hats_only, "no_vest") is False


def test_triggers_event_is_silent_for_rule_types_without_a_person_rule():
    # A zone type with no mapped rule must never start firing person-in-zone.
    for rule_type in ("FOD_WATCH", "NO_SMOKING", "CROWD_WATCH"):
        zone = PPE_ZONE.model_copy(update={"rule_type": rule_type})
        assert triggers_event(zone, "no_vest") is False


class FakeLiveWriter:
    """Always due, so the pipeline annotates a frame even without an event."""

    def due(self) -> bool:
        return True

    def write(self, frame: np.ndarray) -> None:
        pass

    def clean_requested(self) -> bool:
        return False

    def write_clean(self, frame: np.ndarray) -> bool:
        return True


def test_a_compliant_person_in_a_ppe_zone_is_not_highlighted(monkeypatch):
    """Red boxes must mean 'this is a violation', not just 'someone is standing here'."""
    captured: list[set[int]] = []
    real = pipeline_module.draw_overlay

    def spy(frame, zones, detections, inside, engine_on, vest=None, zones_known=True):
        captured.append(set(inside))
        return real(frame, zones, detections, inside, engine_on, vest, zones_known)

    monkeypatch.setattr(pipeline_module, "draw_overlay", spy)

    detections = [[Detection(track_id=1, bbox=TALL_PERSON, confidence=0.91)] for _ in range(20)]
    pipeline = Pipeline(
        camera_id="stand12",
        zones=[PPE_ZONE],
        detector=FakeDetector(detections),
        blurrer=RecordingBlurrer(),
        sink=RecordingSink(),
        engine_on=False,
        start_epoch=1_793_356_933.0,
        live_writer=FakeLiveWriter(),
    )
    for step in range(20):
        pipeline.process(frame_with_vest(), now_s=step / 10)

    assert captured, "the pipeline never annotated a frame"
    assert all(inside == set() for inside in captured)
def test_limit_size_shrinks_only_the_longest_side_above_the_limit():
    from safesight_ml.run import limit_size

    landscape = np.zeros((2160, 3840, 3), dtype=np.uint8)
    portrait = np.zeros((3840, 2160, 3), dtype=np.uint8)
    small = np.zeros((720, 1280, 3), dtype=np.uint8)

    assert limit_size(landscape, 1920).shape == (1080, 1920, 3)
    assert limit_size(portrait, 1920).shape == (1920, 1080, 3)
    assert limit_size(small, 1920) is small
    assert limit_size(landscape, 0) is landscape

def _detector_two_people_one_after_another() -> FakeDetector:
    """Track 1 walks in for 6 s, then track 2 does the same — a re-id or a second worker."""
    frames = []
    for _ in range(10):
        frames.append([])  # nobody: clears any rule state
    for _ in range(60):
        frames.append([Detection(track_id=1, bbox=(0.50, 0.20, 0.60, 0.60), confidence=0.9)])
    for _ in range(150):
        frames.append([])  # long enough for the rule cooldown to expire
    for _ in range(60):
        frames.append([Detection(track_id=2, bbox=(0.50, 0.20, 0.60, 0.60), confidence=0.9)])
    return FakeDetector(frames)


def _run(detector, *, cooldown_s: float, fps: float = 10.0) -> list:
    pipeline = Pipeline(
        camera_id="stand12",
        zones=[ZONE],
        detector=detector,
        blurrer=RecordingBlurrer(),
        sink=RecordingSink(),
        engine_on=True,
        start_epoch=1_793_356_933.0,
        incident_cooldown_s=cooldown_s,
    )
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    emitted = []
    for step in range(280):
        emitted.extend(pipeline.process(frame, now_s=step / fps))
    return emitted


def test_two_presences_in_the_same_zone_raise_two_incidents_without_a_cooldown():
    emitted = _run(_detector_two_people_one_after_another(), cooldown_s=0)
    assert [event.track_id for event in emitted] == [1, 2]


def test_the_same_zone_does_not_raise_the_same_incident_twice_inside_the_cooldown():
    """A worker without a vest must not page the operator every few seconds."""
    emitted = _run(_detector_two_people_one_after_another(), cooldown_s=60)
    assert [event.track_id for event in emitted] == [1]
