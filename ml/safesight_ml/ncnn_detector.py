"""YOLO through NCNN, optionally on the GPU (Vulkan).

NCNN runs the same exported weights on the integrated GPU of a laptop: measured on a
Radeon 780M, YOLO26n takes 17.9 ms there against 41.6 ms on two CPU threads, and the CPU
is left for the blur, the overlay and the other cameras.

The decode is the standard anchor-free head (84 rows: cx, cy, w, h and 80 class scores),
with the letterbox undone before the boxes reach the pipeline. Tracking stays ByteTrack
from ultralytics, fed with our boxes, so track ids keep behaving the same way.

    uv run yolo export model=yolo26n.pt format=ncnn imgsz=640
    uv run python -m safesight_ml.run ... --backend ncnn
"""

from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np

from .detector import Detection

LETTERBOX_FILL = 114  # the padding ultralytics uses, so the weights see what they were trained on


class NcnnError(RuntimeError):
    pass


def letterbox(frame: np.ndarray, size: int = 640) -> tuple[np.ndarray, float, int, int]:
    """Resize keeping the aspect ratio and pad to ``size``; returns the canvas and how to map back."""
    height, width = frame.shape[:2]
    scale = min(size / height, size / width)
    new_h, new_w = int(round(height * scale)), int(round(width * scale))
    canvas = np.full((size, size, 3), LETTERBOX_FILL, np.uint8)
    top, left = (size - new_h) // 2, (size - new_w) // 2
    canvas[top : top + new_h, left : left + new_w] = cv2.resize(frame, (new_w, new_h))
    return canvas, scale, left, top


def decode(
    output: np.ndarray,
    scale: float,
    left: int,
    top: int,
    frame_shape: tuple[int, ...],
    *,
    confidence: float = 0.35,
    class_id: int = 0,
    nms: float = 0.45,
) -> tuple[np.ndarray, np.ndarray]:
    """Raw head -> (boxes in frame pixels, scores), person class only."""
    boxes = output[:4].T
    scores = output[4:].T
    best_class = scores.argmax(axis=1)
    best_score = scores.max(axis=1)
    keep = (best_score >= confidence) & (best_class == class_id)
    if not keep.any():
        return np.zeros((0, 4), np.float32), np.zeros((0,), np.float32)

    box = boxes[keep]
    score = best_score[keep]
    x1 = (box[:, 0] - box[:, 2] / 2 - left) / scale
    y1 = (box[:, 1] - box[:, 3] / 2 - top) / scale
    xywh = np.stack([x1, y1, box[:, 2] / scale, box[:, 3] / scale], axis=1).astype(np.float32)
    # NMSBoxes wants (x, y, w, h); a peak per person survives, duplicates collapse.
    index = np.array(cv2.dnn.NMSBoxes(xywh.tolist(), score.tolist(), confidence, nms)).reshape(-1)
    xywh = xywh[index]
    height, width = frame_shape[:2]
    xyxy = np.stack([xywh[:, 0], xywh[:, 1], xywh[:, 0] + xywh[:, 2], xywh[:, 1] + xywh[:, 3]], axis=1)
    xyxy[:, [0, 2]] = np.clip(xyxy[:, [0, 2]], 0, width)
    xyxy[:, [1, 3]] = np.clip(xyxy[:, [1, 3]], 0, height)
    return xyxy, score[index]


class NcnnDetector:
    """Same interface as ``YoloDetector``: ``detect(frame, frame_index) -> [Detection]``."""

    def __init__(
        self,
        model_dir: str | Path = "yolo26n_ncnn_model",
        *,
        confidence: float = 0.35,
        classes: tuple[int, ...] = (0,),
        use_gpu: bool | None = None,
        threads: int = 0,
    ) -> None:
        try:
            import ncnn
        except ImportError as exc:  # pragma: no cover - depends on the optional extra
            raise NcnnError("ncnn is not installed; run `uv sync --extra ncnn`") from exc
        try:
            from ultralytics.trackers.byte_tracker import BYTETracker
            from ultralytics.utils import IterableSimpleNamespace, YAML
        except ImportError as exc:  # pragma: no cover - depends on the optional extra
            raise NcnnError("ultralytics is not installed; run `uv sync --extra yolo`") from exc

        directory = Path(model_dir)
        param, weights = directory / "model.ncnn.param", directory / "model.ncnn.bin"
        if not param.is_file() or not weights.is_file():
            raise NcnnError(
                f"ncnn model not found in {directory}; run "
                "`uv run yolo export model=yolo26n.pt format=ncnn imgsz=640`"
            )

        self._ncnn = ncnn
        self.model_name = f"ncnn:{directory.name}"
        self.confidence = confidence
        self.classes = classes
        self._net = ncnn.Net()
        # A GPU is only worth it when Vulkan actually sees one; llvmpipe (software) is not.
        gpu_available = ncnn.get_gpu_count() > 0 and "llvmpipe" not in _gpu_names(ncnn)
        self.use_gpu = gpu_available if use_gpu is None else use_gpu
        self._net.opt.use_vulkan_compute = self.use_gpu
        if threads > 0:
            self._net.opt.num_threads = threads
        self._net.load_param(str(param))
        self._net.load_model(str(weights))

        config = YAML.load(str(Path(__file__).resolve().parent.parent / "fixtures" / "bytetrack.yaml"))
        self._tracker = BYTETracker(IterableSimpleNamespace(**config))
        self._boxes_type = _boxes_class()

    def detect(self, frame: np.ndarray, frame_index: int) -> list[Detection]:
        import torch

        canvas, scale, left, top = letterbox(frame)
        tensor = np.ascontiguousarray(canvas[:, :, ::-1].transpose(2, 0, 1).astype(np.float32) / 255.0)
        extractor = self._net.create_extractor()
        extractor.input("in0", self._ncnn.Mat(tensor).clone())
        status, output = extractor.extract("out0")
        if status != 0:
            raise NcnnError(f"ncnn inference failed with status {status}")
        boxes, scores = decode(np.array(output), scale, left, top, frame.shape, confidence=self.confidence)
        tracked = self._track(boxes, scores, frame.shape)
        height, width = frame.shape[:2]
        # The tracker hands back numpy floats; the contract wants an int track id
        # (evt_<camera>_<ms>_<track>) and a plain float confidence.
        return [
            Detection(
                track_id=int(track_id),
                bbox=(float(x1) / width, float(y1) / height, float(x2) / width, float(y2) / height),
                confidence=float(score),
            )
            for x1, y1, x2, y2, track_id, score in tracked
        ]

    def _track(self, boxes: np.ndarray, scores: np.ndarray, shape: tuple[int, ...]) -> np.ndarray:
        """ByteTrack needs one row per detection: x1, y1, x2, y2, score, class."""
        import torch

        rows = np.concatenate([boxes, scores[:, None], np.zeros((len(boxes), 1))], axis=1)
        detections = self._boxes_type(torch.tensor(rows, dtype=torch.float32), orig_shape=shape[:2])
        tracks = self._tracker.update(detections)
        if tracks is None or len(tracks) == 0:
            return np.zeros((0, 6), np.float32)
        # (N, 8): x1, y1, x2, y2, track_id, score, class, index
        return np.stack([tracks[:, 0], tracks[:, 1], tracks[:, 2], tracks[:, 3], tracks[:, 4], tracks[:, 5]], axis=1)

    def people(self, frame: np.ndarray) -> list[tuple[float, float, float, float]]:
        """Person boxes (normalized) without touching tracker state."""
        canvas, scale, left, top = letterbox(frame)
        tensor = np.ascontiguousarray(canvas[:, :, ::-1].transpose(2, 0, 1).astype(np.float32) / 255.0)
        extractor = self._net.create_extractor()
        extractor.input("in0", self._ncnn.Mat(tensor).clone())
        _, output = extractor.extract("out0")
        boxes, _ = decode(np.array(output), scale, left, top, frame.shape, confidence=self.confidence)
        height, width = frame.shape[:2]
        return [(x1 / width, y1 / height, x2 / width, y2 / height) for x1, y1, x2, y2 in boxes]


def _boxes_class() -> type:
    from ultralytics.engine.results import Boxes

    return Boxes


def _gpu_names(ncnn_module) -> str:
    """Device names as ncnn prints them, so a software renderer can be skipped."""
    try:
        return " ".join(ncnn_module.get_gpu_list_ncnn()) if hasattr(ncnn_module, "get_gpu_list_ncnn") else ""
    except Exception:  # noqa: BLE001 - only used to pick a device, never to fail
        return ""
