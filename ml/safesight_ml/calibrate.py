"""Draw a zone on a clip's reference frame, and check that it follows the camera.

    # click the polygon corners on the first frame; Enter prints the JSON polygon
    uv run python -m safesight_ml.calibrate draw --source ../data/videos/clip.mp4

    # zones aligned on frames across the whole clip, as one contact sheet
    uv run python -m safesight_ml.calibrate preview --source ../data/videos/clip.mp4 \
        --zones fixtures/zones/restricted-cam01.json --out out/calib/cam01.jpg

The preview is blurred before it is written, like every other image the edge saves.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

from .align import ZoneAligner, load_reference
from .overlay import draw_overlay
from .privacy import FaceBlurrer
from .run import DEFAULT_FACE_MODEL, load_zones

DRAW_WIDTH = 1280
SHEET_TILE_WIDTH = 640


def draw(source: Path) -> int:  # pragma: no cover - needs a display
    frame = load_reference(source)
    height, width = frame.shape[:2]
    scale = min(1.0, DRAW_WIDTH / width)
    view = cv2.resize(frame, (round(width * scale), round(height * scale)))
    points: list[tuple[float, float]] = []

    def on_click(event, x, y, _flags, _param) -> None:
        if event == cv2.EVENT_LBUTTONDOWN:
            points.append((round(x / view.shape[1], 3), round(y / view.shape[0], 3)))

    window = "zona: click colturi, Backspace sterge, Enter salveaza, Esc iese"
    cv2.namedWindow(window)
    cv2.setMouseCallback(window, on_click)
    while True:
        canvas = view.copy()
        pts = np.array([[x * canvas.shape[1], y * canvas.shape[0]] for x, y in points], dtype=np.int32)
        if len(pts):
            cv2.polylines(canvas, [pts], isClosed=len(pts) > 2, color=(40, 40, 220), thickness=2)
        cv2.imshow(window, canvas)
        key = cv2.waitKey(30) & 0xFF
        if key in (8, 127) and points:
            points.pop()
        elif key in (10, 13) and len(points) >= 3:
            print(json.dumps([list(p) for p in points]))
            break
        elif key == 27:
            break
    cv2.destroyAllWindows()
    return 0


def preview(source: Path, zones_path: Path, out: Path, *, tiles: int, face_model: str, every_n: int) -> int:
    zones = load_zones(zones_path)
    aligner = ZoneAligner(load_reference(source), every_n=every_n)
    blurrer = FaceBlurrer(face_model)
    capture = cv2.VideoCapture(str(source))
    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    wanted = set(np.linspace(0, max(total - 1, 0), tiles).astype(int).tolist())
    sheet: list[np.ndarray] = []
    index = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        aligner.update(frame)
        if index in wanted:
            aligned = aligner.zones(zones)
            tile = draw_overlay(blurrer.blur(frame), aligned or [], [], set(), True, None, aligned is not None)
            cv2.putText(tile, f"frame {index}", (10, tile.shape[0] - 14), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
            h, w = tile.shape[:2]
            sheet.append(cv2.resize(tile, (SHEET_TILE_WIDTH, round(h * SHEET_TILE_WIDTH / w)), interpolation=cv2.INTER_AREA))
        index += 1
    capture.release()
    if not sheet:
        print(f"no frames read from {source}", file=sys.stderr)
        return 2
    rows = [cv2.hconcat(sheet[i : i + 3] + [np.zeros_like(sheet[0])] * (3 - len(sheet[i : i + 3]))) for i in range(0, len(sheet), 3)]
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), cv2.vconcat(rows))
    print(f"{out}: {len(sheet)} frames, align lost {aligner.lost_updates} times")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Draw and check zone polygons")
    sub = parser.add_subparsers(dest="command", required=True)
    draw_cmd = sub.add_parser("draw", help="click a polygon on the reference frame")
    draw_cmd.add_argument("--source", type=Path, required=True)
    prev = sub.add_parser("preview", help="contact sheet of aligned zones across the clip")
    prev.add_argument("--source", type=Path, required=True)
    prev.add_argument("--zones", type=Path, required=True)
    prev.add_argument("--out", type=Path, required=True)
    prev.add_argument("--tiles", type=int, default=6)
    prev.add_argument("--align-every", type=int, default=5)
    prev.add_argument("--face-model", default=DEFAULT_FACE_MODEL)
    args = parser.parse_args(argv)
    if args.command == "draw":
        return draw(args.source)
    return preview(args.source, args.zones, args.out, tiles=args.tiles, face_model=args.face_model, every_n=args.align_every)


if __name__ == "__main__":
    raise SystemExit(main())
