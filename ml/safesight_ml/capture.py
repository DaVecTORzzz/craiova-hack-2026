"""Frame sources. A live stream keeps only its newest frame, so alerts do not lag."""

from __future__ import annotations

import threading
from typing import Protocol

import numpy as np

LIVE_SCHEMES = ("rtsp://", "http://", "https://")


WEBCAM_PREFIX = "webcam"


def webcam_index(source: str) -> int | None:
    """``webcam`` or ``webcam:N`` -> the OpenCV device index; anything else -> None."""
    text = str(source).strip().lower()
    if text == WEBCAM_PREFIX:
        return 0
    prefix = WEBCAM_PREFIX + ":"
    if text.startswith(prefix) and text[len(prefix):].isdigit():
        return int(text[len(prefix):])
    return None


def is_live_source(source: str) -> bool:
    return str(source).lower().startswith(LIVE_SCHEMES) or webcam_index(source) is not None


class Capture(Protocol):
    def read(self) -> tuple[bool, np.ndarray | None]: ...

    def release(self) -> None: ...


class LatestFrameReader:
    """Reads a live capture on a background thread and keeps only the newest frame.

    ``read()`` returns ``(ok, frame, seq)``: ``seq`` counts every frame the source
    delivered, including the ones dropped while the pipeline was busy, so
    ``seq / fps`` stays the stream time. ``ok`` is False once the source ends.
    """

    def __init__(self, capture: Capture) -> None:
        self._capture = capture
        self._cond = threading.Condition()
        self._frame: np.ndarray | None = None
        self._seq = -1
        self._returned = -1
        self._ended = False
        self._stopping = False
        self.dropped = 0
        self._thread = threading.Thread(target=self._run, name="latest-frame-reader", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            while not self._stopping:
                ok, frame = self._capture.read()
                if not ok:
                    break
                with self._cond:
                    if self._seq > self._returned:
                        self.dropped += 1
                    self._frame = frame
                    self._seq += 1
                    self._cond.notify_all()
        finally:
            with self._cond:
                self._ended = True
                self._cond.notify_all()

    def read(self, timeout_s: float | None = None) -> tuple[bool, np.ndarray | None, int]:
        with self._cond:
            if not self._cond.wait_for(lambda: self._seq > self._returned or self._ended, timeout=timeout_s):
                return False, None, self._returned
            if self._seq <= self._returned:
                return False, None, self._returned
            self._returned = self._seq
            return True, self._frame, self._seq

    def release(self) -> None:
        self._stopping = True
        self._thread.join(timeout=2.0)
        # Never release under a read() still in progress; a stuck daemon dies with the process.
        if not self._thread.is_alive():
            self._capture.release()
