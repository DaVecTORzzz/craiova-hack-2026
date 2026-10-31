from __future__ import annotations

import cv2
import numpy as np
import pytest

from safesight_ml.ppe import MIN_SAMPLES, VestTracker, hivis_ratio, vest_sample

PERSON = (0.40, 0.20, 0.60, 0.80)  # 216 px tall on a 360 px frame


def _frame(bgr: tuple[int, int, int]) -> np.ndarray:
    frame = np.full((360, 640, 3), 60, dtype=np.uint8)
    frame[72:288, 256:384] = bgr
    return frame


def _hsv_to_bgr(h: int, s: int, v: int) -> tuple[int, int, int]:
    pixel = cv2.cvtColor(np.uint8([[[h, s, v]]]), cv2.COLOR_HSV2BGR)[0, 0]
    return tuple(int(c) for c in pixel)


def test_pale_yellow_green_vest_counts_but_snow_does_not():
    # cam02, overcast with snow: the vest measured hue ~30, saturation ~63, value ~240.
    assert hivis_ratio(_frame(_hsv_to_bgr(30, 63, 240)), PERSON) > 0.9
    # Snow / white jacket: same hue range, saturation ~12.
    assert hivis_ratio(_frame(_hsv_to_bgr(30, 12, 240)), PERSON) == 0.0
    # Dull olive (low value) stays out.
    assert hivis_ratio(_frame(_hsv_to_bgr(30, 63, 120)), PERSON) == 0.0


def test_small_or_cut_boxes_give_no_sample():
    frame = _frame((0, 120, 255))
    assert vest_sample(frame, PERSON) == pytest.approx(1.0)
    assert vest_sample(frame, (0.45, 0.50, 0.55, 0.60)) is None  # 36 px tall
    assert vest_sample(frame, (0.40, 0.20, 0.60, 1.00)) is None  # cut by the bottom edge
    assert vest_sample(frame, (0.00, 0.20, 0.20, 0.80)) is None  # cut by the left edge


def _feed(tracker: VestTracker, ratio: float | None, n: int, confidence: float = 0.8, px: float = 300) -> str:
    state = "unknown"
    for i in range(n):
        state = tracker.update(1, ratio, confidence, now=i * 0.1, person_px=px)
    return state


def test_states_need_enough_samples():
    tracker = VestTracker()
    assert _feed(tracker, 0.5, MIN_SAMPLES - 1) == "unknown"
    assert _feed(tracker, 0.5, 1) == "vest"


def test_no_vest_needs_a_low_score_and_a_confident_person():
    assert _feed(VestTracker(), 0.0, 10) == "no_vest"
    # Objects mistaken for people scored low with confidence 0.39-0.50.
    assert _feed(VestTracker(), 0.0, 10, confidence=0.4) == "unknown"
    # Shoulder-only hi-vis sits in between: not sure.
    assert _feed(VestTracker(), 0.05, 10) == "unknown"
    # Too small to claim "no vest" (a thin vest strip may be all there is).
    assert _feed(VestTracker(), 0.0, 10, px=120) == "unknown"


def test_frames_without_a_sample_keep_the_state():
    tracker = VestTracker()
    _feed(tracker, 0.5, 10)
    assert _feed(tracker, None, 20) == "vest"


def test_tracks_are_pruned_after_the_ttl():
    tracker = VestTracker(ttl_s=5.0)
    _feed(tracker, 0.5, 10)
    tracker.prune(100.0)
    assert tracker.state(1) == "unknown"
    assert tracker.score(1) is None


def test_a_vest_seen_now_and_then_is_not_no_vest():
    # Small marshaller on broll_cam01: mostly ~0, hi-vis visible in some frames.
    tracker = VestTracker()
    state = "unknown"
    for i in range(60):
        state = tracker.update(1, 0.15 if i % 5 == 0 else 0.0, 0.8, now=i * 0.1)
        assert state != "no_vest", i
    assert state == "unknown"
