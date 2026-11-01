"""Frames per second the edge actually writes, measured from the live frame.

The edge replaces `live/<camera>.jpg` atomically on every rendered frame, so the
file's mtime is a real heartbeat. Counting the changes over a short window gives
the rate the operator actually sees, without the edge having to report anything.

This is why the number is honest: it measures what reached the backend, not what
the edge intended. A slow GPU, a stalled pipeline or a camera nobody is watching
(no frames rendered) all show up as a lower figure or as no figure at all.
"""

from __future__ import annotations

import time
from collections import deque

# Long enough to smooth jitter, short enough to react within a demo.
WINDOW_S = 5.0
# 128 stamps at 60 fps cover ~2 s; enough for the window, cheap to scan.
MAX_STAMPS = 128


class LiveRate:
    """Per-camera frame rate, from consecutive mtime values."""

    def __init__(self, window_s: float = WINDOW_S) -> None:
        self.window_s = window_s
        self._last_version: dict[str, int] = {}
        self._stamps: dict[str, deque[float]] = {}

    def observe(self, camera_id: str, version: int | None) -> float | None:
        """Record a new live frame if the version changed. Returns the current rate."""
        if version is None:
            return self.fps(camera_id)
        if version != self._last_version.get(camera_id):
            self._last_version[camera_id] = version
            now = time.perf_counter()
            stamps = self._stamps.setdefault(camera_id, deque(maxlen=MAX_STAMPS))
            if stamps and now <= stamps[-1]:
                now = stamps[-1] + 1e-6
            stamps.append(now)
        return self.fps(camera_id)

    def fps(self, camera_id: str) -> float | None:
        """Frames per second over the window, or None when there is nothing to measure.

        None means "unknown", never zero: a camera nobody watches renders no frames,
        and reporting 0 fps would look like a fault.
        """
        stamps = self._stamps.get(camera_id)
        if not stamps:
            return None
        now = time.perf_counter()
        recent = [stamp for stamp in stamps if now - stamp <= self.window_s]
        if len(recent) < 2:
            return None
        span = recent[-1] - recent[0]
        if span <= 0:
            return None
        return round((len(recent) - 1) / span, 1)

    def snapshot(self) -> dict[str, float]:
        """Every camera with a measurable rate, for `GET /health`."""
        rates = {camera_id: self.fps(camera_id) for camera_id in self._stamps}
        return {camera_id: rate for camera_id, rate in rates.items() if rate is not None}
