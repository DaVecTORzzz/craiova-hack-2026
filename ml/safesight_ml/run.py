"""CLI for the first edge slice.

Examples:
    uv run python -m safesight_ml.run --fake --engine-on --dry-run
    uv run python -m safesight_ml.run --source clip.mp4 --engine-on --dry-run
    uv run python -m safesight_ml.run --source clip.mp4 --engine-on --post
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import cv2
import httpx
import numpy as np

from .align import ZoneAligner, load_reference
from .capture import LatestFrameReader, is_live_source
from .detector import SyntheticDetector, YoloDetector
from .events import EdgeEvent
from .live import AnnotatedVideoWriter, AsyncLiveWriter, LiveFrameWriter
from .pipeline import Pipeline
from .privacy import FaceBlurrer, NoopBlurrer
from .remote import fetch_edge_config
from .sink import HttpSink, JsonlSink
from .zones import Zone, ZoneMembership

DEFAULT_FACE_MODEL = "models/face_detection_yunet_2023mar.onnx"


def _resolve_fps(requested: float, source: float) -> float:
    for candidate in (requested, source):
        if candidate and math.isfinite(candidate) and candidate > 0:
            return candidate
    return 25.0


def _metrics_source(source: str | None) -> str:
    """Do not write RTSP credentials or tokens from the source URL into metrics."""
    if not source:
        return "fake"
    if "://" not in source:
        return source
    parsed = urlsplit(source)
    host = parsed.hostname or ""
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme, host, parsed.path, "", ""))


def limit_size(frame: np.ndarray, max_size: int) -> np.ndarray:
    """Shrink the frame so its longest side is at most ``max_size`` px; 0 = unchanged."""
    height, width = frame.shape[:2]
    longest = max(height, width)
    if not max_size or longest <= max_size:
        return frame
    scale = max_size / longest
    return cv2.resize(frame, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_AREA)


REFERENCE_MAX_SIZE = 1280


def upload_reference_frames(sink: HttpSink, reference: np.ndarray, zones: list[Zone], camera_id: str, blurrer, detector) -> None:
    """Give the zone editor the frame the zones are drawn on (and aligned to), blurred first.

    Blur runs on the full frame, then the image is shrunk: shrinking first loses faces.
    """
    people = detector.people(reference) if hasattr(detector, "people") else []
    image = limit_size(blurrer.blur(reference, people), REFERENCE_MAX_SIZE)
    for zone in zones:
        if zone.camera_id != camera_id:
            continue
        try:
            print(f"reference frame for {zone.id}: {sink.upload_reference(zone.id, image)}")
        except (httpx.HTTPError, OSError, ValueError) as exc:
            print(f"warn: reference frame upload for {zone.id} failed: {exc}", file=sys.stderr)


def load_zones(path: str | Path) -> list[Zone]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise TypeError("zones file must contain a JSON list")
    return [Zone.model_validate(item) for item in payload]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SafeSight edge — restricted-zone slice")
    parser.add_argument("--source", help="video file or RTSP URL; omit with --fake")
    parser.add_argument("--zones", default="fixtures/zones.json")
    parser.add_argument("--camera-id", default="stand12")
    parser.add_argument("--model", default="yolo26n.pt")
    parser.add_argument("--conf", type=float, default=0.35)
    parser.add_argument("--face-model", default=os.getenv("FACE_MODEL_PATH", DEFAULT_FACE_MODEL))
    parser.add_argument("--out", default="out")
    parser.add_argument("--max-frames", type=int, default=0, help="0 = all frames")
    parser.add_argument("--loop", action="store_true", help="restart a file source at EOF")
    parser.add_argument(
        "--loop-cooldown-s",
        type=float,
        default=60.0,
        help="with --loop, a replayed pass raises events only if the last event is at least this old",
    )
    parser.add_argument("--duration-s", type=float, default=0.0, help="stop after wall-clock seconds; 0 = no limit")
    parser.add_argument(
        "--max-size",
        type=int,
        default=0,
        help="shrink frames so the longest side is at most this many px, right after reading; 0 = off. "
        "Blur, snapshots and the live view use the shrunk frame: check face recall first (ml/README.md)",
    )
    parser.add_argument("--fps", type=float, default=0.0, help="override source FPS")
    parser.add_argument("--engine-on", dest="engine_on", action="store_true", default=None)
    parser.add_argument("--engine-off", dest="engine_on", action="store_false")
    parser.add_argument("--fake", action="store_true", help="synthetic frames; no model, no video")
    transport = parser.add_mutually_exclusive_group()
    transport.add_argument("--post", action="store_true", help="POST to backend instead of dry-run")
    transport.add_argument("--dry-run", dest="post", action="store_false", help="write JSONL locally (default)")
    parser.add_argument("--api-url", default=os.getenv("API_URL", "http://localhost:8000"))
    parser.add_argument("--edge-token", default=os.getenv("EDGE_TOKEN", "dev-edge-token"))
    parser.add_argument("--remote-config", action="store_true", help="load zones and engine_on from GET /edge/zones")
    parser.add_argument("--config-refresh-s", type=float, default=30.0, help="remote config poll interval")
    parser.add_argument("--live-dir", default=os.getenv("LIVE_DIR", ""), help="write live/{camera}.jpg for backend MJPEG")
    parser.add_argument(
        "--live-when-watched",
        action="store_true",
        help="render the live frame (and run the live YuNet) only while live/{camera}.watch is fresh; "
        "the backend touches it while a /stream client is connected. Detection and alerts always run",
    )
    parser.add_argument("--live-fps", type=float, default=30.0, help="cap for live frames per second (the blur may allow fewer)")
    parser.add_argument("--annotated-video", type=Path, help="write every frame, blurred and annotated, to this MP4")
    parser.add_argument(
        "--align-reference",
        type=Path,
        help="video or image the zones were drawn on (first frame); zones then follow camera pan/zoom",
    )
    parser.add_argument("--align-every", type=int, default=5, help="re-estimate camera motion every N frames")
    parser.add_argument(
        "--zone-margin",
        type=float,
        default=0.10,
        help="feet must be this many person-heights inside a zone to enter, and outside to leave; 0 = bare point test",
    )
    parser.add_argument("--metrics-json", type=Path, help="write a JSON summary for this run")
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
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.duration_s < 0:
        parser.error("--duration-s must be >= 0")
    if args.loop_cooldown_s < 0:
        parser.error("--loop-cooldown-s must be >= 0")
    if args.zone_margin < 0:
        parser.error("--zone-margin must be >= 0")
    if args.live_fps <= 0:
        parser.error("--live-fps must be > 0")
    if args.max_size < 0:
        parser.error("--max-size must be >= 0")
    if args.align_every < 1:
        parser.error("--align-every must be >= 1")
    engine_on = args.fake if args.engine_on is None else args.engine_on
    zones: list[Zone] = []

    if args.remote_config:
        try:
            config = fetch_edge_config(args.api_url, args.edge_token, args.camera_id)
            zones = config.zones
            engine_on = config.engine_on
            print(f"remote config v{config.config_version}: engine_on={engine_on}, zones={len(zones)}")
        except (httpx.HTTPError, ValueError, OSError) as exc:
            print(f"warn: remote config failed ({exc}); using local zones", file=sys.stderr)

    if not zones:
        zones = load_zones(args.zones)

    if not zones:
        print("no zones loaded", file=sys.stderr)
        return 2

    start_epoch = time.time()
    run_started = time.perf_counter()

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

    live_writer = (
        AsyncLiveWriter(
            LiveFrameWriter(args.live_dir, args.camera_id),
            faces=blurrer if isinstance(blurrer, FaceBlurrer) else None,
            max_fps=args.live_fps,
            watch_path=Path(args.live_dir) / f"{args.camera_id}.watch" if args.live_when_watched else None,
        )
        if args.live_dir
        else None
    )
    aligner = None
    if args.align_reference:
        try:
            reference = load_reference(args.align_reference)
        except OSError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        aligner = ZoneAligner(reference, every_n=args.align_every)
        if isinstance(sink, HttpSink):
            upload_reference_frames(sink, reference, zones, args.camera_id, blurrer, detector)
    pipeline = Pipeline(
        camera_id=args.camera_id,
        zones=zones,
        detector=detector,
        blurrer=blurrer,
        sink=sink,
        engine_on=engine_on,
        start_epoch=start_epoch,
        clock=time.time,
        live_writer=live_writer,
        aligner=aligner,
        membership=ZoneMembership(margin=args.zone_margin),
    )

    total = 0
    dropped_frames = 0
    event_rows: list[dict] = []

    last_event_at: float | None = None

    def record_events(emitted: list[EdgeEvent]) -> None:
        nonlocal last_event_at
        if emitted:
            last_event_at = time.monotonic()
        for event in emitted:
            event_rows.append(
                {
                    "event_id": event.event_id,
                    "type": event.type,
                    "zone_id": event.zone_id,
                    "track_id": event.track_id,
                    "confidence": event.confidence.detector,
                    "detected_at": event.detected_at.isoformat(),
                }
            )

    if args.fake:
        fps = args.fps or 10.0
        if args.annotated_video:
            pipeline.video_writer = AnnotatedVideoWriter(args.annotated_video, fps)
        limit = args.max_frames or 60
        for frame_index in range(limit):
            frame = _draw_fake_frame(frame_index, detector, pipeline.zones)
            try:
                record_events(pipeline.process(frame, frame_index / fps))
            except (httpx.HTTPError, OSError, ValueError) as exc:
                print(f"warn: frame {frame_index} failed: {exc}", file=sys.stderr)
            total += 1
            if args.duration_s and time.monotonic() - run_started >= args.duration_s:
                break
    else:
        capture = cv2.VideoCapture(args.source)
        if not capture.isOpened():
            print(f"could not open source: {_metrics_source(args.source)}", file=sys.stderr)
            return 2
        fps = _resolve_fps(args.fps, capture.get(cv2.CAP_PROP_FPS))
        if args.annotated_video:
            pipeline.video_writer = AnnotatedVideoWriter(args.annotated_video, fps)
        frame_index = 0
        last_refresh = time.monotonic()
        last_config_version: int | None = None
        # A live stream must not queue frames behind a slow pipeline: keep the newest one.
        reader = LatestFrameReader(capture) if is_live_source(args.source) else None
        try:
            while True:
                read_started = time.perf_counter()
                if reader is not None:
                    ok, frame, frame_index = reader.read()
                else:
                    ok, frame = capture.read()
                if ok:
                    frame = limit_size(frame, args.max_size)
                pipeline.timer.add("read", time.perf_counter() - read_started)
                if not ok:
                    if args.loop and reader is None:
                        capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        # Each pass replays the same scene; without this the demo raises
                        # (and notifies) the same incident every few seconds.
                        pipeline.emit_events = (
                            last_event_at is None or time.monotonic() - last_event_at >= args.loop_cooldown_s
                        )
                        continue
                    break
                try:
                    record_events(pipeline.process(frame, frame_index / fps))
                except (httpx.HTTPError, OSError, ValueError) as exc:
                    print(f"warn: frame {frame_index} failed: {exc}", file=sys.stderr)
                total += 1
                frame_index += 1

                if args.duration_s and time.monotonic() - run_started >= args.duration_s:
                    break

                if args.remote_config and time.monotonic() - last_refresh >= args.config_refresh_s:
                    # Also after a failure: a backend that is down must not be retried on every frame.
                    last_refresh = time.monotonic()
                    try:
                        config = fetch_edge_config(args.api_url, args.edge_token, args.camera_id)
                        pipeline.set_config(config.zones, config.engine_on)
                        if config.config_version != last_config_version:
                            print(f"remote config v{config.config_version}: engine_on={config.engine_on}")
                            last_config_version = config.config_version
                    except (httpx.HTTPError, ValueError, OSError) as exc:
                        print(f"warn: remote config refresh failed ({exc})", file=sys.stderr)

                if args.max_frames and total >= args.max_frames:
                    break
        finally:
            if reader is not None:
                dropped_frames = reader.dropped
                reader.release()
            else:
                capture.release()

    if isinstance(sink, HttpSink):
        sink.close()
    if pipeline.video_writer is not None:
        pipeline.video_writer.close()
    if live_writer is not None:
        live_writer.close()

    elapsed_s = max(time.perf_counter() - run_started, 0.001)
    event_types: dict[str, int] = {}
    for row in event_rows:
        event_types[row["type"]] = event_types.get(row["type"], 0) + 1
    metrics = {
        "source": _metrics_source(args.source),
        "camera_id": args.camera_id,
        "frames": total,
        "events": len(event_rows),
        "event_types": event_types,
        "event_details": event_rows,
        "elapsed_s": round(elapsed_s, 3),
        "fps": round(total / elapsed_s, 2),
        "dropped_frames": dropped_frames,
        "live_frames": live_writer.written if live_writer is not None else 0,
        "live": (
            {
                **{k: v for k, v in live_writer.stats.items() if not k.endswith("_s")},
                "render_ms": round(1000 * live_writer.stats["render_s"] / max(live_writer.written, 1), 1),
                "face_pass_ms": round(1000 * live_writer.stats["faces_s"] / max(live_writer.stats["passes"], 1), 1),
            }
            if live_writer is not None
            else None
        ),
        "zone_transitions": pipeline.membership.transitions,
        "align_lost_updates": aligner.lost_updates if aligner is not None else None,
        "stages": pipeline.timer.summary(),
        "engine_on": pipeline.engine_on,
        "sink": "http" if args.post else "jsonl",
        "model": detector.model_name,
        "max_frames": args.max_frames,
        "duration_s": args.duration_s,
    }
    if args.metrics_json:
        args.metrics_json.parent.mkdir(parents=True, exist_ok=True)
        args.metrics_json.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        f"frames={total} events={len(event_rows)} engine_on={pipeline.engine_on} "
        f"sink={'http' if args.post else 'jsonl'} elapsed={elapsed_s:.2f}s fps={metrics['fps']}"
    )
    stages = " ".join(f"{name}={row['mean_ms']}ms" for name, row in metrics["stages"].items())
    print(f"stages: {stages} dropped={dropped_frames}")
    if not args.post:
        print(f"events: {Path(args.out) / 'events.jsonl'}")
        print(f"snapshots: {Path(args.out) / 'snapshots'}")
    if pipeline.video_writer is not None:
        print(f"annotated video: {args.annotated_video} ({pipeline.video_writer.frames} frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
