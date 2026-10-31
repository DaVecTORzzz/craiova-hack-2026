"""Write the latest blurred frame for the backend MJPEG stream."""

from __future__ import annotations

import os
import time
from pathlib import Path

import cv2
import numpy as np


class LiveFrameWriter:
    def __init__(self, directory: str | Path, camera_id: str, *, interval_s: float = 0.5, max_width: int = 1280) -> None:
        self.directory = Path(directory)
        self.camera_id = camera_id
        self.interval_s = interval_s
        self.max_width = max_width
        self.path = self.directory / f"{camera_id}.jpg"
        self.directory.mkdir(parents=True, exist_ok=True)
        self._last_write = 0.0

    def due(self) -> bool:
        return time.monotonic() - self._last_write >= self.interval_s

    def write(self, frame: np.ndarray) -> bool:
        height, width = frame.shape[:2]
        if width > self.max_width:
            frame = cv2.resize(frame, (self.max_width, round(height * self.max_width / width)), interpolation=cv2.INTER_AREA)
        ok, data = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ok:
            return False
        # Write then rename, so the MJPEG reader never sees a half-written JPEG.
        tmp = self.path.with_suffix(".jpg.tmp")
        tmp.write_bytes(data.tobytes())
        os.replace(tmp, self.path)
        self._last_write = time.monotonic()
        return True


class AnnotatedVideoWriter:
    """Every processed frame, blurred and annotated, as a local MP4 to watch the detection."""

    def __init__(self, path: str | Path, fps: float, *, max_width: int = 1280) -> None:
        self.path = Path(path)
        self.fps = fps
        self.max_width = max_width
        self.frames = 0
        self._writer: cv2.VideoWriter | None = None

    def write(self, frame: np.ndarray) -> None:
        height, width = frame.shape[:2]
        if width > self.max_width:
            frame = cv2.resize(frame, (self.max_width, round(height * self.max_width / width)), interpolation=cv2.INTER_AREA)
        if self._writer is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            size = (frame.shape[1], frame.shape[0])
            self._writer = cv2.VideoWriter(str(self.path), cv2.VideoWriter_fourcc(*"mp4v"), self.fps, size)
            if not self._writer.isOpened():
                raise OSError(f"could not open video writer at {self.path}")
        self._writer.write(frame)
        self.frames += 1

    def close(self) -> None:
        if self._writer is not None:
            self._writer.release()
            self._writer = None
