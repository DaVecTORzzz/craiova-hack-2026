"""Privacy guard: blur faces before any snapshot is saved or uploaded."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import cv2
import numpy as np


class PrivacyError(RuntimeError):
    pass


class Blurrer(Protocol):
    def blur(self, frame: np.ndarray, boxes: list[tuple[float, float, float, float]] = ()) -> np.ndarray: ...


class FaceBlurrer:
    """OpenCV YuNet face detector + Gaussian blur.

    Fails closed: if the model is missing, no image is written.
    """

    def __init__(self, model_path: str | Path, *, score_threshold: float = 0.6) -> None:
        path = Path(model_path)
        if not path.is_file():
            raise PrivacyError(
                f"face model not found at {path}; run ml/scripts/fetch_face_model.sh"
            )
        self._detector = cv2.FaceDetectorYN.create(
            str(path),
            "",
            (320, 320),
            score_threshold=score_threshold,
        )

    def detect_faces(self, frame: np.ndarray) -> list[tuple[int, int, int, int]]:
        """Face boxes ``(x, y, width, height)`` in the source frame."""
        height, width = frame.shape[:2]
        self._detector.setInputSize((width, height))
        _, detections = self._detector.detect(frame)
        if detections is None:
            return []
        return [(int(x), int(y), int(w), int(h)) for x, y, w, h in detections[:, :4]]

    def blur(self, frame: np.ndarray, boxes: list[tuple[float, float, float, float]] = ()) -> np.ndarray:
        height, width = frame.shape[:2]

        output = frame.copy()
        for x, y, w, h in self.detect_faces(frame):
            self._blur_box(output, x, y, x + w, y + h, width, height)

        # Safety net for small/distant faces: blur the top of every person box.
        for x1, y1, x2, y2 in boxes:
            px1 = int(x1 * width)
            py1 = int(y1 * height)
            px2 = int(x2 * width)
            py2 = int(y2 * height)
            head_height = max(1, int((py2 - py1) * 0.35))
            self._blur_box(output, px1, py1, px2, py1 + head_height, width, height)

        return output

    @staticmethod
    def _blur_box(
        frame: np.ndarray,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        width: int,
        height: int,
    ) -> None:
        margin = max(1, int(0.2 * max(x2 - x1, y2 - y1)))
        left = max(0, x1 - margin)
        top = max(0, y1 - margin)
        right = min(width, x2 + margin)
        bottom = min(height, y2 + margin)
        roi = frame[top:bottom, left:right]
        if roi.size:
            frame[top:bottom, left:right] = cv2.GaussianBlur(roi, (0, 0), sigmaX=25)


class NoopBlurrer:
    """Only for synthetic frames and tests; never for airport footage."""

    def blur(self, frame: np.ndarray, boxes: list[tuple[float, float, float, float]] = ()) -> np.ndarray:
        return frame
