"""Hi-vis check by colour, without a trained model.

Display only: it labels people whose torso shows fluorescent orange or yellow-green.
Every worker in our clips wears hi-vis, so a low score means "not sure", not "no vest";
no NO_PPE event is raised from it until a clip with a real violation validates the rule.
"""

from __future__ import annotations

import cv2
import numpy as np

from .detector import Box

# Measured on the demo clips: vests 0.10-0.69 (snow lowers saturation), dark clothes below 0.03,
# jackets with hi-vis only on the shoulders 0.03-0.07 (shown as "vesta ?").
HIVIS_MIN = 0.10


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
    return float(((orange | yellow_green) > 0).mean())


class VestTracker:
    """Smooths the per-frame ratio per track so the label does not flicker."""

    def __init__(self, alpha: float = 0.2) -> None:
        self.alpha = alpha
        self._scores: dict[int, float] = {}

    def update(self, track_id: int, ratio: float | None) -> float | None:
        previous = self._scores.get(track_id)
        if ratio is None:
            return previous
        score = ratio if previous is None else previous + self.alpha * (ratio - previous)
        self._scores[track_id] = score
        return score

