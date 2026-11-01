#!/usr/bin/env python3
"""YuNet pe cadru întreg vs YuNet pe decupaje din jurul persoanelor.

Ideea: cutia persoanei îți spune unde pot fi fețe. Decupezi, mărești, detectezi.
Fața devine mai mare în decupaj, deci și mai ușor de găsit, și mult mai ieftin.

Comparăm pe aceleași cadre:
  * timpul de detecție
  * câte fețe găsește fiecare
  * recall-ul decupajelor față de cadrul întreg (câte fețe cunoscute ratează)
  * fețele găsite doar de decupaje (candidați la fals pozitiv)

    uv run python experiments/face_roi.py --frames 40
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import cv2
import numpy as np

ML = Path(__file__).resolve().parents[1]
VIDEOS = ML.parent / "data" / "videos"
YUNET = ML / "models" / "face_detection_yunet_2023mar.onnx"

CLIPS = [
    "2026-10-30_restricted-zone_cam01_persoana-langa-motor.mp4",
    "2026-10-30_broll_cam03_lucratori-cu-veste-apron.mp4",
]

MARGIN = 0.25       # cât lățime în plus în jurul persoanei
CROP_HEIGHT = 320   # la ce înălțime mărim decupajul înainte de YuNet
MIN_CROP = 48       # nu are sens să rulăm YuNet pe mai puțin


def iou(a, b) -> float:
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


class Yunet:
    def __init__(self) -> None:
        self._det = cv2.FaceDetectorYN.create(str(YUNET), "", (320, 320), 0.6, 0.3, 5000)

    def on(self, image: np.ndarray) -> list[tuple[float, float, float, float]]:
        h, w = image.shape[:2]
        if h < MIN_CROP or w < MIN_CROP:
            return []
        self._det.setInputSize((w, h))
        _, raw = self._det.detect(image)
        if raw is None:
            return []
        return [(float(x), float(y), float(x + bw), float(y + bh)) for x, y, bw, bh in raw[:, :4]]


def roi_faces(det: Yunet, frame: np.ndarray, people: list[tuple[int, int, int, int]]):
    h, w = frame.shape[:2]
    found = []
    crops = 0
    for x1, y1, x2, y2 in people:
        mx, my = int((x2 - x1) * MARGIN), int((y2 - y1) * MARGIN)
        cx1, cy1 = max(0, x1 - mx), max(0, y1 - my)
        cx2, cy2 = min(w, x2 + mx), min(h, y2 + my)
        if cx2 - cx1 < MIN_CROP or cy2 - cy1 < MIN_CROP:
            continue
        crop = frame[cy1:cy2, cx1:cx2]
        scale = CROP_HEIGHT / crop.shape[0]
        if scale != 1.0:
            crop = cv2.resize(crop, (max(MIN_CROP, int(crop.shape[1] * scale)), CROP_HEIGHT))
        crops += 1
        for fx1, fy1, fx2, fy2 in det.on(crop):
            inv = 1.0 / scale
            found.append((cx1 + fx1 * inv, cy1 + fy1 * inv, cx1 + fx2 * inv, cy1 + fy2 * inv))
    return found, crops


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", type=int, default=40)
    parser.add_argument("--model", default="yolo26n.pt")
    args = parser.parse_args()

    from ultralytics import YOLO

    yolo = YOLO(args.model)
    det = Yunet()

    print(f"{'clip':30} {'strategie':14} {'ms/cadru':>9} {'fețe':>6} {'recall':>8} {'doar ROI':>9}")

    for clip in CLIPS:
        cap = cv2.VideoCapture(str(VIDEOS / clip))
        frames = []
        while len(frames) < args.frames:
            ok, f = cap.read()
            if not ok:
                break
            frames.append(f)
        cap.release()
        if not frames:
            continue

        t_full = t_roi = 0.0
        full_all, roi_all, crops_total = [], [], 0

        for frame in frames:
            res = yolo.predict(frame, classes=[0], conf=0.35, verbose=False)[0]
            people = [tuple(int(v) for v in b) for b in res.boxes.xyxy.cpu().numpy()]

            t0 = time.perf_counter()
            full = det.on(frame)
            t_full += time.perf_counter() - t0

            t0 = time.perf_counter()
            roi, crops = roi_faces(det, frame, people)
            t_roi += time.perf_counter() - t0
            crops_total += crops

            full_all.append(full)
            roi_all.append(roi)

        n = len(frames)
        total_full = sum(len(f) for f in full_all)
        total_roi = sum(len(r) for r in roi_all)

        hit = sum(1 for f, r in zip(full_all, roi_all)
                  for box in f if any(iou(box, rb) >= 0.3 for rb in r))
        only_roi = sum(1 for f, r in zip(full_all, roi_all)
                       for box in r if not any(iou(box, fb) >= 0.3 for fb in f))

        print(f"{clip[:30]:30} {'cadru întreg':14} {t_full/n*1000:9.1f} {total_full:6} {'100%':>8} {'—':>9}")
        print(f"{clip[:30]:30} {'decupaje':14} {t_roi/n*1000:9.1f} {total_roi:6} "
              f"{100*hit/max(total_full,1):7.0f}% {only_roi:9}")
        print(f"{'':30} decupaje/cadru: {crops_total/n:.1f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
