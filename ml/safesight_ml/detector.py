"""Detectors: a deterministic fake for tests/demo, and a YOLO26 adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

Box = tuple[float, float, float, float]


@dataclass(frozen=True)
class Detection:
    track_id: int
    bbox: Box  # normalized x1, y1, x2, y2
    confidence: float
    class_id: int = 0

    @property
    def foot_point(self) -> tuple[float, float]:
        """Bottom-center of the box: the point that enters an apron zone."""
        x1, _, x2, y2 = self.bbox
        return ((x1 + x2) / 2.0, y2)


class Detector(Protocol):
    model_name: str

    def detect(self, frame: np.ndarray, frame_index: int) -> list[Detection]: ...


class FakeDetector:
    """Replays a fixed list of detections per frame. No model, no GPU."""

    model_name = "fake-person-v1"

    def __init__(self, frames: list[list[Detection]] | None = None) -> None:
        self.frames = frames or []

    def detect(self, frame: np.ndarray, frame_index: int) -> list[Detection]:
        if not self.frames:
            return []
        if frame_index < len(self.frames):
            return self.frames[frame_index]
        return self.frames[-1]


class SyntheticDetector:
    """A person-shaped box crossing the engine zone. Used by ``--fake``."""

    model_name = "synthetic-person-v1"

    def __init__(self, total_frames: int = 60) -> None:
        self.total_frames = total_frames

    def detect(self, frame: np.ndarray, frame_index: int) -> list[Detection]:
        if frame_index >= self.total_frames:
            return []
        # x moves 0.20 -> 0.80; bottom stays at 0.60, inside the fixture polygon.
        progress = frame_index / max(self.total_frames - 1, 1)
        center_x = 0.20 + 0.60 * progress
        box: Box = (center_x - 0.06, 0.20, center_x + 0.06, 0.60)
        return [Detection(track_id=1, bbox=box, confidence=0.91)]


class YoloDetector:
    """Ultralytics YOLO26 with built-in ByteTrack.

    Requires the optional ``yolo`` extra: ``uv sync --extra yolo``.
    """

    def __init__(
        self,
        model_path: str = "yolo26n.pt",
        *,
        confidence: float = 0.35,
        classes: tuple[int, ...] = (0,),
    ) -> None:
        try:
            from ultralytics import YOLO
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise RuntimeError("ultralytics is not installed; run `uv sync --extra yolo`") from exc

        self.model = YOLO(model_path)
        self.model_name = Path(model_path).name
        self.confidence = confidence
        self.classes = classes

    def detect(self, frame: np.ndarray, frame_index: int) -> list[Detection]:
        results = self.model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            conf=self.confidence,
            classes=list(self.classes),
            verbose=False,
        )
        if not results:
            return []
        boxes = results[0].boxes
        if boxes is None or boxes.id is None:
            return []

        height, width = frame.shape[:2]
        detections: list[Detection] = []
        for box, score, track_id in zip(boxes.xyxy.cpu().numpy(), boxes.conf.cpu().numpy(), boxes.id.cpu().numpy()):
            x1, y1, x2, y2 = (float(v) for v in box)
            detections.append(
                Detection(
                    track_id=int(track_id),
                    bbox=(x1 / width, y1 / height, x2 / width, y2 / height),
                    confidence=float(score),
                )
            )
        return detections
