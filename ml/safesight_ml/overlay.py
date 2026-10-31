"""Draw zones and detections on an already blurred frame for the live view and snapshots."""

from __future__ import annotations

import cv2
import numpy as np

from .detector import Detection
from .ppe import VestState
from .zones import Zone

# BGR
RED = (40, 40, 220)
GREEN = (70, 170, 60)
GREY = (150, 150, 150)
WHITE = (255, 255, 255)
AMBER = (0, 160, 255)

# ASCII: Hershey fonts have no diacritics.
VEST_LABEL = {"vest": " | vesta", "no_vest": " | FARA VESTA", "unknown": " | vesta ?"}


def zone_active(zone: Zone, engine_on: bool) -> bool:
    return zone.active_when == "always" or engine_on


def draw_overlay(
    frame: np.ndarray,
    zones: list[Zone],
    detections: list[Detection],
    inside: set[int],
    engine_on: bool,
    vest: dict[int, VestState] | None = None,
    zones_known: bool = True,
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
        if vest is not None and vest.get(detection.track_id) == "no_vest" and detection.track_id not in inside:
            color = AMBER
        cv2.rectangle(out, p1, p2, color, thick)
        foot = (round((x1 + x2) / 2 * width), p2[1])
        cv2.circle(out, foot, thick + 2, color, -1)
        text = f"persoana #{detection.track_id} {detection.confidence:.2f}"
        if vest is not None:
            text += VEST_LABEL[vest.get(detection.track_id, "unknown")]
        _label(out, text, p1, color, font, thick)

    parts = [f"{len(detections)} persoane", f"{len(inside)} in zona"]
    # The engine only matters where a zone depends on it (not on a PPE-only camera).
    if any(zone.active_when == "engine_on" for zone in zones):
        parts.insert(0, "MOTOR PORNIT" if engine_on else "MOTOR OPRIT")
    text = " | ".join(parts)
    if not zones_known:
        text += " | ZONA NEALINIATA"
    _label(out, text, (0, 0), RED if inside else GREY, font, thick, below=True)
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


def draw_alert(frame: np.ndarray, text: str) -> np.ndarray:
    """Red banner across the bottom of the frame, shown for a moment after an event."""
    out = frame.copy()
    height, width = out.shape[:2]
    scale = max(width / 1280.0, 0.5)
    thick = max(2, round(2 * scale))
    font = 0.8 * scale
    (tw, th), base = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font, thick)
    bar = th + base + 4 * thick
    cv2.rectangle(out, (0, height - bar), (width, height), RED, -1)
    cv2.putText(out, text, ((width - tw) // 2, height - base - 2 * thick), cv2.FONT_HERSHEY_SIMPLEX, font, WHITE, thick, cv2.LINE_AA)
    return out
