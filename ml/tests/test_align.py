from __future__ import annotations

import cv2
import numpy as np
import pytest

from safesight_ml.align import ZoneAligner, _plausible
from safesight_ml.detector import Detection, FakeDetector
from safesight_ml.pipeline import Pipeline
from safesight_ml.zones import Zone

ZONE = Zone(
    id="engine-left",
    camera_id="stand12",
    rule_type="RESTRICTED",
    severity="CRITICAL",
    debounce_s=0.0,
    polygon=[(0.40, 0.40), (0.60, 0.40), (0.60, 0.60), (0.40, 0.60)],
)


def _scene(seed: int = 7) -> np.ndarray:
    """Textured 'apron' with enough corners for ORB."""
    rng = np.random.default_rng(seed)
    image = np.full((540, 960, 3), 110, dtype=np.uint8)
    for _ in range(400):
        x, y = int(rng.integers(0, 940)), int(rng.integers(0, 520))
        w, h = int(rng.integers(6, 40)), int(rng.integers(6, 40))
        color = tuple(int(c) for c in rng.integers(0, 255, 3))
        cv2.rectangle(image, (x, y), (x + w, y + h), color, -1)
    return image


def _shift(image: np.ndarray, dx: int, dy: int) -> np.ndarray:
    matrix = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(image, matrix, (image.shape[1], image.shape[0]), borderValue=(110, 110, 110))


def test_zone_follows_a_camera_pan():
    reference = _scene()
    aligner = ZoneAligner(reference, every_n=1)

    assert aligner.update(_shift(reference, 96, 54))  # scene moves +10% right, +10% down
    (zone,) = aligner.zones([ZONE])

    assert zone.polygon[0] == pytest.approx((0.50, 0.50), abs=0.01)
    assert zone.polygon[2] == pytest.approx((0.70, 0.70), abs=0.01)


def test_zone_is_unknown_when_the_view_cannot_be_matched():
    aligner = ZoneAligner(_scene(), every_n=1)

    assert not aligner.update(np.full((540, 960, 3), 110, dtype=np.uint8))
    assert aligner.zones([ZONE]) is None
    assert aligner.lost_updates == 1


def test_aligner_only_re_estimates_every_n_frames():
    reference = _scene()
    aligner = ZoneAligner(reference, every_n=3)
    blank = np.full_like(reference, 110)

    assert aligner.update(blank) is False  # call 1 estimates and fails
    assert aligner.update(reference) is False  # calls 2-3 keep the last estimate
    assert aligner.update(reference) is False
    assert aligner.update(reference) is True  # call 4 estimates again


def test_degenerate_homographies_are_rejected():
    assert _plausible(np.eye(3))
    assert not _plausible(np.diag([10.0, 10.0, 1.0]))
    assert not _plausible(np.full((3, 3), np.nan))


class _Sink:
    def __init__(self) -> None:
        self.events = []

    def store_snapshot(self, event_id, frame):
        return f"/snapshots/{event_id}.jpg"

    def emit(self, event):
        self.events.append(event)


class _Blur:
    def blur(self, frame, boxes=()):
        return frame


def _pipeline(aligner: ZoneAligner, sink: _Sink) -> Pipeline:
    # Feet at (0.55, 0.55): inside the zone as drawn on the reference frame.
    person = Detection(track_id=1, bbox=(0.50, 0.30, 0.60, 0.55), confidence=0.9)
    return Pipeline(
        camera_id="stand12",
        zones=[ZONE],
        detector=FakeDetector([[person]] * 20),
        blurrer=_Blur(),
        sink=sink,
        engine_on=True,
        aligner=aligner,
    )


def test_no_event_while_the_zone_is_unknown():
    reference = _scene()
    sink = _Sink()
    pipeline = _pipeline(ZoneAligner(reference, every_n=1), sink)
    blank = np.full_like(reference, 110)

    for index in range(10):
        pipeline.process(blank, index * 0.1)

    assert sink.events == []


def test_event_uses_the_aligned_zone():
    reference = _scene()
    sink = _Sink()
    pipeline = _pipeline(ZoneAligner(reference, every_n=1), sink)

    for index in range(10):
        pipeline.process(reference, index * 0.1)

    assert len(sink.events) == 1
    assert sink.events[0].zone_id == "engine-left"


def test_no_event_when_the_pan_moves_the_zone_away_from_the_person():
    reference = _scene()
    sink = _Sink()
    pipeline = _pipeline(ZoneAligner(reference, every_n=1), sink)
    # Scene moves 15% left and up: the zone is now 0.25..0.45, the feet stay at 0.55.
    panned = _shift(reference, -144, -81)

    for index in range(10):
        pipeline.process(panned, index * 0.1)

    assert sink.events == []


# Zone ids the backend seeds per camera (backend/app/seed.py). POST /edge/events
# rejects any other zone_id with 404, so every per-clip fixture must reuse one.
SEEDED_ZONE_IDS = {
    "stand12": {"engine-left", "apron-stand12"},
    "taxiway-b": {"taxiway-b"},
    "baggage-area": {"baggage-area"},
}


def test_per_clip_fixtures_use_seeded_cameras_and_zone_ids():
    from pathlib import Path

    from safesight_ml.run import load_zones

    fixtures = sorted((Path(__file__).resolve().parents[1] / "fixtures" / "zones").glob("*.json"))
    assert len(fixtures) == 6
    for path in fixtures:
        for zone in load_zones(path):
            assert zone.id in SEEDED_ZONE_IDS[zone.camera_id], path.name
