"""Write the latest blurred frame for the backend MJPEG stream."""

from __future__ import annotations

import os
import threading
from collections import deque
import time
from collections.abc import Callable
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


Render = Callable[[object], np.ndarray]  # render(blurrer) -> blurred + annotated frame


class AsyncLiveWriter:
    """Renders and writes the live frame off the detection loop, at up to ``max_fps``.

    Full-frame YuNet is too slow to run on every live frame, so it runs on its own thread
    on the newest frame, and each live frame is held until a YuNet pass on a *later* frame
    has finished. The frame is then blurred with the faces of the pass just before it and
    the pass just after it (grown by ``face_margin``), plus its own person boxes. A face
    that appears between two passes is caught by the next one, so the live view runs one
    YuNet pass (well under a second) behind real time; detection and alerts do not wait.

    ``faces`` is anything with ``detect_faces(frame) -> [(x, y, w, h) px]``; ``None``
    (synthetic frames) renders at once with ``NoopBlurrer``.
    """

    def __init__(
        self,
        writer: LiveFrameWriter,
        *,
        faces=None,
        max_fps: float = 15.0,
        face_margin: float = 0.5,
        max_queue: int = 30,
        max_wait_s: float = 3.0,
    ) -> None:
        self.writer = writer
        self.faces = faces
        self.min_interval_s = 1.0 / max_fps
        self.face_margin = face_margin
        self.max_wait_s = max_wait_s
        self.written = 0
        self.dropped = 0
        self._cond = threading.Condition()
        self._queue: deque[tuple[float, np.ndarray, Render]] = deque(maxlen=max_queue)
        self._to_detect: tuple[float, np.ndarray] | None = None
        self._passes: deque[tuple[float, list[tuple[float, float, float, float]]]] = deque(maxlen=8)
        self._closed = False
        self._threads = [threading.Thread(target=self._write_loop, name="live-writer", daemon=True)]
        if faces is not None:
            self._threads.append(threading.Thread(target=self._detect_loop, name="live-faces", daemon=True))
        for thread in self._threads:
            thread.start()

    def submit(self, frame: np.ndarray, render: Render) -> None:
        now = time.monotonic()
        with self._cond:
            if len(self._queue) == self._queue.maxlen:
                self.dropped += 1
            self._queue.append((now, frame, render))
            self._to_detect = (now, frame)
            self._cond.notify_all()

    def _detect_loop(self) -> None:
        while True:
            with self._cond:
                self._cond.wait_for(lambda: self._to_detect is not None or self._closed)
                if self._closed:
                    return
                stamp, frame = self._to_detect
                self._to_detect = None
            height, width = frame.shape[:2]
            found = [(x / width, y / height, w / width, h / height) for x, y, w, h in self.faces.detect_faces(frame)]
            with self._cond:
                self._passes.append((stamp, found))
                self._cond.notify_all()

    def _ready(self) -> bool:
        if not self._queue:
            return False
        stamp = self._queue[0][0]
        return self.faces is None or any(t >= stamp for t, _ in self._passes) or time.monotonic() - stamp > self.max_wait_s

    def _write_loop(self) -> None:
        from .privacy import FixedFacesBlurrer, NoopBlurrer

        last = 0.0
        while True:
            with self._cond:
                self._cond.wait_for(lambda: self._ready() or self._closed)
                if self._closed:
                    return
                stamp, frame, render = self._queue.popleft()
                before = [faces for t, faces in self._passes if t <= stamp][-1:]
                after = [faces for t, faces in self._passes if t >= stamp][:1]
            if self.faces is None:
                blurrer = NoopBlurrer()
            elif not after:
                self.dropped += 1  # no YuNet pass after it in time: never show it unchecked
                continue
            else:
                blurrer = FixedFacesBlurrer([box for faces in before + after for box in faces], self.face_margin)
            if time.monotonic() - last < self.min_interval_s:
                self.dropped += 1  # over the fps cap: skip, the next frame is newer anyway
                continue
            last = time.monotonic()
            try:
                if self.writer.write(render(blurrer)):
                    self.written += 1
            except Exception as exc:  # noqa: BLE001 - a bad frame must not kill the live view
                print(f"warn: live frame failed: {exc}")

    def close(self) -> None:
        with self._cond:
            self._closed = True
            self._cond.notify_all()
        for thread in self._threads:
            thread.join(timeout=5.0)


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
