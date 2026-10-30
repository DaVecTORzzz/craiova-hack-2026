"""CLI for the first edge slice.

Examples:
    uv run python -m safetarmac_ml.run --fake --engine-on --dry-run
    uv run python -m safetarmac_ml.run --source clip.mp4 --engine-on --dry-run
    uv run python -m safetarmac_ml.run --source clip.mp4 --engine-on --post
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from .detector import SyntheticDetector, YoloDetector
from .pipeline import Pipeline
from .privacy import FaceBlurrer, NoopBlurrer
from .sink import HttpSink, JsonlSink
from .zones import Zone

DEFAULT_FACE_MODEL = "models/face_detection_yunet_2023mar.onnx"


def _resolve_fps(requested: float, source: float) -> float:
    for candidate in (requested, source):
        if candidate and math.isfinite(candidate) and candidate > 0:
            return candidate
    return 25.0


def load_zones(path: str | Path) -> list[Zone]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise TypeError("zones file must contain a JSON list")
    return [Zone.model_validate(item) for item in payload]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SafeTarmac edge — restricted-zone slice")
    parser.add_argument("--source", help="video file or RTSP URL; omit with --fake")
    parser.add_argument("--zones", default="fixtures/zones.json")
    parser.add_argument("--camera-id", default="stand12")
    parser.add_argument("--model", default="yolo26n.pt")
    parser.add_argument("--conf", type=float, default=0.35)
    parser.add_argument("--face-model", default=os.getenv("FACE_MODEL_PATH", DEFAULT_FACE_MODEL))
    parser.add_argument("--out", default="out")
    parser.add_argument("--max-frames", type=int, default=0, help="0 = all frames")
    parser.add_argument("--fps", type=float, default=0.0, help="override source FPS")
    parser.add_argument("--engine-on", dest="engine_on", action="store_true", default=None)
    parser.add_argument("--engine-off", dest="engine_on", action="store_false")
    parser.add_argument("--fake", action="store_true", help="synthetic frames; no model, no video")
    transport = parser.add_mutually_exclusive_group()
    transport.add_argument("--post", action="store_true", help="POST to backend instead of dry-run")
    transport.add_argument("--dry-run", dest="post", action="store_false", help="write JSONL locally (default)")
    parser.add_argument("--api-url", default=os.getenv("API_URL", "http://localhost:8000"))
    parser.add_argument("--edge-token", default=os.getenv("EDGE_TOKEN", "dev-edge-token"))
    return parser


def _draw_fake_frame(frame_index: int, detector: SyntheticDetector, zones: list[Zone]) -> np.ndarray:
    height, width = 360, 640
    frame = np.full((height, width, 3), 238, dtype=np.uint8)
    for zone in zones:
        points = np.array([[int(x * width), int(y * height)] for x, y in zone.polygon], dtype=np.int32)
        cv2.polylines(frame, [points], isClosed=True, color=(200, 120, 40), thickness=2)
        cv2.putText(frame, zone.id, tuple(points[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (120, 70, 20), 1, cv2.LINE_AA)

    for detection in detector.detect(frame, frame_index):
        x1, y1, x2, y2 = detection.bbox
        p1 = (int(x1 * width), int(y1 * height))
        p2 = (int(x2 * width), int(y2 * height))
        cv2.rectangle(frame, p1, p2, (40, 160, 70), 2)
        cv2.putText(frame, f"person #{detection.track_id}", (p1[0], max(18, p1[1] - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (30, 120, 50), 1, cv2.LINE_AA)

    cv2.putText(frame, f"frame {frame_index}", (12, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (70, 70, 70), 1, cv2.LINE_AA)
    return frame


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    zones = load_zones(args.zones)
    if not zones:
        print("no zones loaded", file=sys.stderr)
        return 2

    engine_on = args.fake if args.engine_on is None else args.engine_on
    start_epoch = time.time()

    if args.fake:
        detector = SyntheticDetector(total_frames=args.max_frames or 60)
        blurrer = NoopBlurrer()
    else:
        if not args.source:
            print("--source is required unless --fake is used", file=sys.stderr)
            return 2
        detector = YoloDetector(args.model, confidence=args.conf)
        blurrer = FaceBlurrer(args.face_model)

    sink = HttpSink(args.api_url, args.edge_token) if args.post else JsonlSink(args.out)

    pipeline = Pipeline(
        camera_id=args.camera_id,
        zones=zones,
        detector=detector,
        blurrer=blurrer,
        sink=sink,
        engine_on=engine_on,
        start_epoch=start_epoch,
    )

    total = 0
    events = 0

    if args.fake:
        fps = args.fps or 10.0
        limit = args.max_frames or 60
        for frame_index in range(limit):
            frame = _draw_fake_frame(frame_index, detector, pipeline.zones)
            events += len(pipeline.process(frame, frame_index / fps))
            total += 1
    else:
        capture = cv2.VideoCapture(args.source)
        if not capture.isOpened():
            print(f"could not open source: {args.source}", file=sys.stderr)
            return 2
        fps = _resolve_fps(args.fps, capture.get(cv2.CAP_PROP_FPS))
        frame_index = 0
        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                events += len(pipeline.process(frame, frame_index / fps))
                total += 1
                frame_index += 1
                if args.max_frames and total >= args.max_frames:
                    break
        finally:
            capture.release()

    if isinstance(sink, HttpSink):
        sink.close()

    print(f"frames={total} events={events} engine_on={engine_on} sink={'http' if args.post else 'jsonl'}")
    if not args.post:
        print(f"events: {Path(args.out) / 'events.jsonl'}")
        print(f"snapshots: {Path(args.out) / 'snapshots'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
