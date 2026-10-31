"""Privacy guard: blur faces before any snapshot is saved or uploaded."""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np
import onnxruntime as ort

# YuNet is published with a fixed 640x640 input. ONNX Runtime cannot grow it, so the
# declared shape is made dynamic at load, the same way FaceDetectorYN re-shapes the
# graph to whatever frame it is given.
YUNET_STRIDES = (8, 16, 32)
# The fusion layers in the graph require both sides to be multiples of 32; the frame is
# padded with empty rows at the bottom, which does not move any real pixel.
YUNET_ALIGN = 32
# Measured on the demo clips at 1920x1080, 1/2/3/4/6 threads: 53/35/29/26/25 ms per
# frame. Four is the knee, and three cameras then fit in 12 of 16 hardware threads
# instead of one cv2.dnn call taking all of them.
FACE_THREADS = int(os.getenv("SAFESIGHT_FACE_THREADS", "4"))


class PrivacyError(RuntimeError):
    pass


class Blurrer(Protocol):
    def blur(self, frame: np.ndarray, boxes: list[tuple[float, float, float, float]] = ()) -> np.ndarray: ...


class _Yunet:
    """YuNet through ONNX Runtime: the same model and the same maths as
    ``cv2.FaceDetectorYN`` (anchor-free, ``sqrt(cls * obj)``, greedy NMS), 1.6x faster on
    the demo clips at 1920x1080 (42 ms -> 26 ms) and with identical detections."""

    def __init__(self, model: Path, *, score_threshold: float, nms_threshold: float = 0.3) -> None:
        options = ort.SessionOptions()
        options.intra_op_num_threads = FACE_THREADS
        options.inter_op_num_threads = 1
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        # The exported graph still declares the 640x640 output grids, so every run logs a
        # shape mismatch that is expected and harmless; errors are still shown.
        options.log_severity_level = 3
        try:
            self._session = ort.InferenceSession(
                _dynamic_input(model), options, providers=["CPUExecutionProvider"]
            )
        except Exception as exc:  # noqa: BLE001 - any load failure must stop the edge, not skip the blur
            hint = (
                " (the int8bq model uses block quantization, which ONNX Runtime rejects; "
                "use models/face_detection_yunet_2023mar.onnx)"
                if "int8" in model.stem
                else ""
            )
            raise PrivacyError(f"could not load face model {model}: {exc}{hint}") from exc
        self._input = self._session.get_inputs()[0].name
        self.score_threshold = score_threshold
        self.nms_threshold = nms_threshold
        self._blob: np.ndarray | None = None
        self._padded_size: tuple[int, int] = (0, 0)

    def detect(self, frame: np.ndarray) -> list[tuple[int, int, int, int]]:
        height, width = frame.shape[:2]
        padded_h = -(-height // YUNET_ALIGN) * YUNET_ALIGN
        padded_w = -(-width // YUNET_ALIGN) * YUNET_ALIGN
        if self._blob is None or self._padded_size != (padded_w, padded_h):
            # Reused every frame; the pad rows and columns keep their zeros.
            self._blob = np.zeros((1, 3, padded_h, padded_w), np.float32)
            self._padded_size = (padded_w, padded_h)
        # OpenCV feeds blobFromImage defaults: BGR, no mean, no resize. Same here, or the
        # scores drift (0.60 instead of 0.769 on a known face).
        self._blob[0, :, :height, :width] = frame.transpose(2, 0, 1)
        outputs = self._session.run(None, {self._input: self._blob})
        boxes = _decode_yunet(outputs, padded_w, padded_h, self.score_threshold, self.nms_threshold)
        # (x, y, w, h) in the original frame; the padding added rows and columns after the
        # image, so no rescale is applied (OpenCV does not rescale either).
        return [(int(x), int(y), int(w), int(h)) for x, y, w, h in boxes]


def _dynamic_input(model: Path) -> bytes:
    """The published model with symbolic height/width, as bytes, so nothing is written."""
    import onnx  # only needed here; keeps the edge import path short

    loaded = onnx.load(str(model))
    dims = loaded.graph.input[0].type.tensor_type.shape.dim
    dims[0].dim_value = 1
    for axis, name in ((2, "height"), (3, "width")):
        dims[axis].ClearField("dim_value")
        dims[axis].dim_param = name
    return loaded.SerializeToString()


def _decode_yunet(
    outputs: list[np.ndarray], padded_w: int, padded_h: int, score_threshold: float, nms_threshold: float
) -> np.ndarray:
    boxes: list[np.ndarray] = []
    scores: list[np.ndarray] = []
    for index, stride in enumerate(YUNET_STRIDES):
        cls = np.clip(outputs[index].reshape(-1), 0.0, 1.0)
        obj = np.clip(outputs[index + len(YUNET_STRIDES)].reshape(-1), 0.0, 1.0)
        deltas = outputs[index + 2 * len(YUNET_STRIDES)].reshape(-1, 4)
        score = np.sqrt(cls * obj)
        cols = padded_w // stride
        cells = np.flatnonzero(score >= score_threshold)
        if not cells.size:
            continue
        row, col = cells // cols, cells % cols
        centre_x = (col + deltas[cells, 0]) * stride
        centre_y = (row + deltas[cells, 1]) * stride
        box_w = np.exp(deltas[cells, 2]) * stride
        box_h = np.exp(deltas[cells, 3]) * stride
        boxes.append(
            np.stack(
                [centre_x - box_w / 2, centre_y - box_h / 2, centre_x + box_w / 2, centre_y + box_h / 2],
                axis=1,
            )
        )
        scores.append(score[cells])
    if not boxes:
        return np.zeros((0, 4), np.float32)

    box = np.concatenate(boxes)
    keep = _nms(box, np.concatenate(scores), nms_threshold)
    kept = box[keep]
    return np.stack(
        [kept[:, 0], kept[:, 1], kept[:, 2] - kept[:, 0], kept[:, 3] - kept[:, 1]], axis=1
    )


def _nms(box: np.ndarray, score: np.ndarray, threshold: float) -> np.ndarray:
    order = np.argsort(-score)
    keep: list[int] = []
    while order.size:
        best = int(order[0])
        keep.append(best)
        rest = order[1:]
        if not rest.size:
            break
        overlap_w = np.maximum(0.0, np.minimum(box[best, 2], box[rest, 2]) - np.maximum(box[best, 0], box[rest, 0]))
        overlap_h = np.maximum(0.0, np.minimum(box[best, 3], box[rest, 3]) - np.maximum(box[best, 1], box[rest, 1]))
        inter = overlap_w * overlap_h
        union = (
            (box[best, 2] - box[best, 0]) * (box[best, 3] - box[best, 1])
            + (box[rest, 2] - box[rest, 0]) * (box[rest, 3] - box[rest, 1])
            - inter
        )
        with np.errstate(divide="ignore", invalid="ignore"):
            overlap = np.where(union > 0, inter / union, 0.0)
        order = rest[overlap <= threshold]
    return np.array(keep, dtype=int)


class FaceBlurrer:
    """YuNet face detector + Gaussian blur.

    Fails closed: if the model is missing or cannot be loaded, no image is written.
    """

    def __init__(self, model_path: str | Path, *, score_threshold: float = 0.6) -> None:
        path = Path(model_path)
        if not path.is_file():
            raise PrivacyError(
                f"face model not found at {path}; run ml/scripts/fetch_face_model.sh"
            )
        # The live view blurs on its own thread while event snapshots blur on the main one;
        # one YuNet instance must not run both at once.
        self._lock = threading.Lock()
        self._detector = _Yunet(path, score_threshold=score_threshold)

    def detect_faces(self, frame: np.ndarray) -> list[tuple[int, int, int, int]]:
        """Face boxes ``(x, y, width, height)`` in the source frame."""
        with self._lock:
            return self._detector.detect(frame)

    def blur(self, frame: np.ndarray, boxes: list[tuple[float, float, float, float]] = ()) -> np.ndarray:
        return self.blur_with_faces(frame, self.detect_faces(frame), boxes)

    @classmethod
    def blur_with_faces(
        cls,
        frame: np.ndarray,
        faces: list[tuple[int, int, int, int]],
        boxes: list[tuple[float, float, float, float]] = (),
    ) -> np.ndarray:
        """Blur the given face boxes (px) and the top of every person box (normalized)."""
        height, width = frame.shape[:2]

        output = frame.copy()
        for x, y, w, h in faces:
            cls._blur_box(output, x, y, x + w, y + h, width, height)

        # Safety net for small/distant faces: blur the top of every person box.
        for x1, y1, x2, y2 in boxes:
            px1 = int(x1 * width)
            py1 = int(y1 * height)
            px2 = int(x2 * width)
            py2 = int(y2 * height)
            head_height = max(1, int((py2 - py1) * 0.35))
            cls._blur_box(output, px1, py1, px2, py1 + head_height, width, height)

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
            frame[top:bottom, left:right] = _strong_blur(roi)


class FixedFacesBlurrer:
    """Blurs a frame with face boxes found by an earlier YuNet pass (normalized), grown by
    ``margin`` of their size, plus the top of every person box of the current frame."""

    def __init__(self, faces: list[tuple[float, float, float, float]], margin: float = 0.5) -> None:
        self.faces = faces
        self.margin = margin

    def blur(self, frame: np.ndarray, boxes: list[tuple[float, float, float, float]] = ()) -> np.ndarray:
        height, width = frame.shape[:2]
        grown = []
        for x, y, w, h in self.faces:
            dx, dy = w * self.margin, h * self.margin
            grown.append((int((x - dx) * width), int((y - dy) * height), int((w + 2 * dx) * width), int((h + 2 * dy) * height)))
        return FaceBlurrer.blur_with_faces(frame, grown, boxes)


BLUR_SCALE = 8


def _strong_blur(roi: np.ndarray) -> np.ndarray:
    """Same anonymising strength as GaussianBlur(sigma=25), ~40x cheaper: shrink 8x,
    blur, scale back. A 300x300 region costs ~0.7 ms instead of ~27 ms."""
    height, width = roi.shape[:2]
    small = cv2.resize(
        roi,
        (max(1, width // BLUR_SCALE), max(1, height // BLUR_SCALE)),
        interpolation=cv2.INTER_AREA,
    )
    small = cv2.GaussianBlur(small, (0, 0), sigmaX=25 / BLUR_SCALE)
    return cv2.resize(small, (width, height), interpolation=cv2.INTER_LINEAR)


class NoopBlurrer:
    """Only for synthetic frames and tests; never for airport footage."""

    def blur(self, frame: np.ndarray, boxes: list[tuple[float, float, float, float]] = ()) -> np.ndarray:
        return frame
