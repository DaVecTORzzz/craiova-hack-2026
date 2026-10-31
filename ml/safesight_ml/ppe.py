"""Hi-vis vest check by colour, without a trained model.

Each person track gets one of three states: ``vest``, ``no_vest`` or ``unknown``.
A frame only counts when the person is big enough and fully inside the frame, and
``no_vest`` also needs a confident person detection, because the low scores on our
clips came from partial boxes and from objects mistaken for people, not from people
without a vest.

``no_vest`` raises ``NO_PPE`` in a ``PPE_REQUIRED`` zone that requires ``hi_vis_vest``;
``unknown`` never does. This is still a colour heuristic, not a trained classifier.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Literal

import cv2
import numpy as np

from .detector import Box

VestState = Literal["vest", "no_vest", "unknown"]

# Measured on the demo clips (31 Oct 2026). People with a vest: track medians 0.07-0.76.
# Labelled stills: with vest 0.52, without vest 0.00.
HIVIS_MIN = 0.10  # at or above: vest
NO_VEST_MAX = 0.03  # below, with a confident detection: no vest; in between: unknown
MIN_PERSON_PX = 80  # smaller people have too few torso pixels to judge
# Claiming "no vest" needs more pixels: the marshaller on broll_cam01 (112-122 px, back
# to the camera, in shade) shows his vest only as a thin dark-orange strip.
MIN_PERSON_PX_NO_VEST = 150
MIN_SAMPLES = 5  # good frames before a track gets a state
# "no vest" looks at the last RECENT good frames: a worn vest shows up at least now and
# then (the marshaller on broll_cam01 dips below 0.03 in 37% of frames, p90 0.15), so
# it needs the 90th percentile of the window below NO_VEST_MAX, not just a low average.
RECENT = 30
MIN_SAMPLES_NO_VEST = 10
MIN_CONFIDENCE_NO_VEST = 0.5  # boxes on barriers/equipment scored 0.39-0.50
EDGE = 0.005  # a box this close to the frame border is cut


def hivis_ratio(frame: np.ndarray, bbox: Box) -> float | None:
    """Share of fluorescent pixels in the torso band of a person box (raw, unblurred frame)."""
    height, width = frame.shape[:2]
    x1, y1, x2, y2 = bbox
    bw, bh = x2 - x1, y2 - y1
    left, right = int((x1 + 0.2 * bw) * width), int((x2 - 0.2 * bw) * width)
    top, bottom = int((y1 + 0.15 * bh) * height), int((y1 + 0.55 * bh) * height)
    crop = frame[max(0, top):max(0, bottom), max(0, left):max(0, right)]
    if crop.size == 0:
        return None
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    orange = cv2.inRange(hsv, (3, 140, 140), (22, 255, 255))
    yellow_green = cv2.inRange(hsv, (23, 100, 120), (65, 255, 255))
    # Overcast or snow washes a yellow-green vest out (saturation ~60 on cam02); keep it
    # when it is still bright. Snow and white surfaces stay out (saturation ~10).
    pale_yellow_green = cv2.inRange(hsv, (23, 45, 170), (65, 255, 255))
    return float(((orange | yellow_green | pale_yellow_green) > 0).mean())


def vest_sample(frame: np.ndarray, bbox: Box) -> float | None:
    """The ratio for one frame, or None when the box is too small or cut by the frame."""
    x1, y1, x2, y2 = bbox
    if (y2 - y1) * frame.shape[0] < MIN_PERSON_PX:
        return None
    if x1 <= EDGE or y1 <= EDGE or x2 >= 1 - EDGE or y2 >= 1 - EDGE:
        return None
    return hivis_ratio(frame, bbox)


@dataclass
class _Track:
    score: float = 0.0
    samples: int = 0
    confidence: float = 0.0
    last_seen: float = 0.0
    recent: deque[float] = field(default_factory=lambda: deque(maxlen=RECENT))
    recent_px: deque[float] = field(default_factory=lambda: deque(maxlen=RECENT))


class VestTracker:
    """Smooths the per-frame ratio per track and turns it into a vest state."""

    def __init__(self, alpha: float = 0.2, ttl_s: float = 10.0) -> None:
        self.alpha = alpha
        self.ttl_s = ttl_s
        self._tracks: dict[int, _Track] = {}

    def update(
        self,
        track_id: int,
        ratio: float | None,
        confidence: float = 1.0,
        now: float = 0.0,
        person_px: float = float("inf"),
    ) -> VestState:
        track = self._tracks.setdefault(track_id, _Track())
        track.last_seen = now
        if ratio is not None:
            if track.samples == 0:
                track.score, track.confidence = ratio, confidence
            else:
                track.score += self.alpha * (ratio - track.score)
                track.confidence += self.alpha * (confidence - track.confidence)
            track.samples += 1
            track.recent.append(ratio)
            track.recent_px.append(person_px)
        return self.state(track_id)

    def state(self, track_id: int) -> VestState:
        track = self._tracks.get(track_id)
        if track is None or track.samples < MIN_SAMPLES:
            return "unknown"
        if track.score >= HIVIS_MIN:
            return "vest"
        if (
            track.samples >= MIN_SAMPLES_NO_VEST
            and float(np.percentile(track.recent, 90)) < NO_VEST_MAX
            and float(np.median(track.recent_px)) >= MIN_PERSON_PX_NO_VEST
            and track.confidence >= MIN_CONFIDENCE_NO_VEST
        ):
            return "no_vest"
        return "unknown"

    def score(self, track_id: int) -> float | None:
        track = self._tracks.get(track_id)
        return None if track is None or track.samples == 0 else track.score

    def prune(self, now: float) -> None:
        """Drop tracks not seen for ``ttl_s``; a short occlusion keeps the state."""
        for track_id, track in list(self._tracks.items()):
            if now - track.last_seen >= self.ttl_s:
                del self._tracks[track_id]
