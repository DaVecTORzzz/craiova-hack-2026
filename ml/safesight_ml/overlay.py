"""Draw zones and detections on an already blurred frame for the live view and snapshots."""

from __future__ import annotations

import cv2
import numpy as np

from .detector import Detection
from .zones import Zone

# BGR
RED = (40, 40, 220)
GREEN = (70, 170, 60)
GREY = (150, 150, 150)
WHITE = (255, 255, 255)


def zone_active(zone: Zone, engine_on: bool) -> bool:
    return zone.active_when == "always" or engine_on


def draw_overlay(
    frame: np.ndarray,
    zones: list[Zone],
    detections: list[Detection],
    inside: set[int],
    engine_on: bool,
) -> np.ndarray:
    """Return a copy with zone polygons, boxes and labels. ``inside`` holds track ids in an active zone.

    Text is ASCII on purpose: OpenCV's Hershey fonts have no diacritics.
    """
    out = frame.copy()
    height, width = out.shape[:2]
    scale = max(width / 1280.0, 0.5)
    thick = max(2, round(2 * scale))
    font = 0.55 * scale

    fill = out.copy()
    for zone in zones:
        color = RED if zone_active(zone, engine_on) else GREY
        points = np.array([[round(x * width), round(y * height)] for x, y in zone.polygon], dtype=np.int32)
        cv2.fillPoly(fill, [points], color)
        cv2.polylines(out, [points], isClosed=True, color=color, thickness=thick)
        _label(out, zone.id, (int(points[:, 0].min()), int(points[:, 1].min())), color, font, thick)
    cv2.addWeighted(fill, 0.18, out, 0.82, 0, dst=out)

    for detection in detections:
        x1, y1, x2, y2 = detection.bbox
        p1 = (round(x1 * width), round(y1 * height))
        p2 = (round(x2 * width), round(y2 * height))
        color = RED if detection.track_id in inside else GREEN
        cv2.rectangle(out, p1, p2, color, thick)
        foot = (round((x1 + x2) / 2 * width), p2[1])
        cv2.circle(out, foot, thick + 2, color, -1)
        _label(out, f"persoana #{detection.track_id} {detection.confidence:.2f}", p1, color, font, thick)

    status = "MOTOR PORNIT" if engine_on else "MOTOR OPRIT"
    _label(out, f"{status} | {len(detections)} persoane | {len(inside)} in zona", (0, 0), RED if inside else GREY, font, thick, below=True)
    return out


def _label(
    frame: np.ndarray,
    text: str,
    anchor: tuple[int, int],
    color: tuple[int, int, int],
    font: float,
    thick: int,
    *,
    below: bool = False,
) -> None:
    (tw, th), base = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font, max(1, thick - 1))
    pad = thick + 2
    x = max(0, anchor[0])
    top = anchor[1] if below else max(0, anchor[1] - th - base - 2 * pad)
    cv2.rectangle(frame, (x, top), (x + tw + 2 * pad, top + th + base + 2 * pad), color, -1)
    cv2.putText(
        frame,
        text,
        (x + pad, top + pad + th),
        cv2.FONT_HERSHEY_SIMPLEX,
        font,
        WHITE,
        max(1, thick - 1),
        cv2.LINE_AA,
    )
