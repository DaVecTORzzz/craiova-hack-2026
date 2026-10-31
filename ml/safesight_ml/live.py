"""Write the latest blurred frame for the backend MJPEG stream."""

from __future__ import annotations

import time
from pathlib import Path

import cv2
import numpy as np


class LiveFrameWriter:
    def __init__(self, directory: str | Path, camera_id: str, *, interval_s: float = 0.5) -> None:
        self.directory = Path(directory)
        self.camera_id = camera_id
        self.interval_s = interval_s
        self.path = self.directory / f"{camera_id}.jpg"
        self.directory.mkdir(parents=True, exist_ok=True)
        self._last_write = 0.0

    def due(self) -> bool:
        return time.monotonic() - self._last_write >= self.interval_s

    def write(self, frame: np.ndarray) -> bool:
        if not cv2.imwrite(str(self.path), frame):
            return False
        self._last_write = time.monotonic()
        return True
