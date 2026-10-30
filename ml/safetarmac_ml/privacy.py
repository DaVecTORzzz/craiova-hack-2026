"""Privacy guard: blur faces before any snapshot is saved or uploaded."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import cv2
import numpy as np


class PrivacyError(RuntimeError):
    pass


class Blurrer(Protocol):
    def blur(self, frame: np.ndarray) -> np.ndarray: ...


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

    def blur(self, frame: np.ndarray) -> np.ndarray:
        height, width = frame.shape[:2]
        self._detector.setInputSize((width, height))
        _, faces = self._detector.detect(frame)
        if faces is None or len(faces) == 0:
            return frame

        output = frame.copy()
        for face in faces:
            x, y, w, h = (int(v) for v in face[:4])
            margin = int(0.2 * max(w, h))
            x1 = max(0, x - margin)
            y1 = max(0, y - margin)
            x2 = min(width, x + w + margin)
            y2 = min(height, y + h + margin)
            roi = output[y1:y2, x1:x2]
            if roi.size:
                output[y1:y2, x1:x2] = cv2.GaussianBlur(roi, (0, 0), sigmaX=25)
        return output


class NoopBlurrer:
    """Only for synthetic frames and tests; never for airport footage."""

    def blur(self, frame: np.ndarray) -> np.ndarray:
        return frame
