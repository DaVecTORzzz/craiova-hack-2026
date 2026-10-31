"""Audit saved snapshots for faces that the blur step missed.

    uv run python -m safesight_ml.privacy_audit --dir ../backend/snapshots
    uv run python -m safesight_ml.privacy_audit --dir out/snapshots --json

Exit codes: 0 = clean, 1 = faces found, 2 = missing model/dir, no images or unreadable image.
The detector is the same YuNet model used by ``FaceBlurrer``; this is a check on
already-blurred output, not a replacement for blurring at the edge.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .privacy import FaceBlurrer, PrivacyError

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
Detect = Callable[[np.ndarray], list[tuple[int, int, int, int]]]


@dataclass(frozen=True)
class Finding:
    path: str
    faces: int


def iter_images(root: Path) -> list[Path]:
    """All image files under ``root`` (or ``root`` itself), sorted."""
    if root.is_file():
        return [root] if root.suffix.lower() in IMAGE_SUFFIXES else []
    return sorted(
        path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def scan_images(images: Iterable[tuple[Path, np.ndarray]], detect: Detect) -> list[Finding]:
    findings: list[Finding] = []
    for path, image in images:
        faces = detect(image)
        if faces:
            findings.append(Finding(path=str(path), faces=len(faces)))
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check saved snapshots for unblurred faces.")
    parser.add_argument("--dir", type=Path, required=True, help="snapshot directory or one image")
    parser.add_argument(
        "--model",
        default="models/face_detection_yunet_2023mar.onnx",
        help="YuNet ONNX model",
    )
    parser.add_argument("--threshold", type=float, default=0.6, help="YuNet score threshold")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root: Path = args.dir
    if not root.exists():
        print(f"snapshot path not found: {root}")
        return 2

    paths = iter_images(root)
    if not paths:
        print(f"no images found under {root}")
        return 2

    try:
        blurrer = FaceBlurrer(args.model, score_threshold=args.threshold)
    except PrivacyError as exc:
        print(str(exc))
        return 2

    readable: list[tuple[Path, np.ndarray]] = []
    unreadable: list[str] = []
    for path in paths:
        image = cv2.imread(str(path))
        if image is None:
            unreadable.append(str(path))
        else:
            readable.append((path, image))

    findings = scan_images(readable, blurrer.detect_faces)
    payload = {
        "dir": str(root),
        "images": len(readable),
        "unreadable": unreadable,
        "findings": [{"path": finding.path, "faces": finding.faces} for finding in findings],
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for finding in findings:
            print(f"FAIL: {finding.faces} face(s) detected in {finding.path}")
        if unreadable:
            for path in unreadable:
                print(f"ERROR: unreadable image {path}")
        if not findings and not unreadable:
            print(f"OK: {len(readable)} image(s), 0 faces detected")

    if unreadable:
        return 2
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
