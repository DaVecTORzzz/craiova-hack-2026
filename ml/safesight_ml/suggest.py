"""Propuneri de zone, derivate din ce vede camera.

Două surse, independente:

* **activitate** — YOLO urmărește oamenii pe câteva zeci de cadre, iar punctele lor de
  sprijin se grupează: unde stă lumea de fapt devine o zonă de lucru (PPE obligatoriu).
* **echipament** — un detector open-vocabulary (Grounding DINO) găsește „jet engine",
  „boarding stairs", „baggage cart" într-un singur cadru, iar cutia se extinde spre sol,
  unde stă de fapt lumea: aceea e zona periculoasă (RESTRICTED).

Rezultatul e o listă de propuneri; operatorul le acceptă sau nu din editor. Analiza nu
rulează în bucla live: Grounding DINO costă ~20 s pe CPU pentru un cadru, deci e o acțiune
explicită („analizează scena"), nu ceva ce se face pe fiecare cadru.

    uv run python -m safesight_ml.suggest --source clip.mp4 --camera-id stand12
    uv run python -m safesight_ml.suggest --source clip.mp4 --out proposals.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

import cv2
import numpy as np

# Echipamentul care primește zonă periculoasă, cu felul zonei sugerat.
EQUIPMENT_PROMPTS = ("jet engine. boarding stairs. baggage cart. tow tractor.")
EQUIPMENT_ZONES = {
    "jet engine": ("Zonă motor", "RESTRICTED", "CRITICAL"),
    "boarding stairs": ("Zonă scări îmbarcare", "RESTRICTED", "CRITICAL"),
    "baggage cart": ("Zonă cărucioare bagaje", "RESTRICTED", "WARNING"),
    "tow tractor": ("Zonă tractare", "RESTRICTED", "WARNING"),
}

ACTIVITY_MARGIN = 0.03  # cât creștem poligonul de activitate, ca omul să fie înăuntru
EQUIPMENT_SIDE_PAD = 0.25  # cât lățime în plus în jurul echipamentului
EQUIPMENT_GROUND_DROP = 1.2  # cât coborâm sub echipament, spre zona de pericol
CLUSTER_RADIUS = 0.06  # ~6% din diagonală: un grup de oameni, nu două
CLUSTER_MINIMUM = 12  # sub atât e un trecător, nu o zonă de lucru


@dataclass
class Proposal:
    id: str
    camera_id: str
    kind: str  # "activity" | "equipment"
    label: str
    rule_type: str
    severity: str
    polygon: list[tuple[float, float]]
    score: float = 0.0
    evidence: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)


def cluster_points(points: np.ndarray, radius: float = CLUSTER_RADIUS, minimum: int = CLUSTER_MINIMUM) -> list[np.ndarray]:
    """DBSCAN suficient pentru câteva sute de puncte, fără dependențe."""
    if len(points) == 0:
        return []
    labels = np.full(len(points), -1)
    groups: list[np.ndarray] = []
    for index in range(len(points)):
        if labels[index] != -1:
            continue
        neighbours = np.linalg.norm(points - points[index], axis=1) <= radius
        if neighbours.sum() < minimum:
            continue
        label = len(groups)
        labels[neighbours] = label
        pending = list(np.flatnonzero(neighbours))
        while pending:
            candidate = pending.pop()
            close = np.linalg.norm(points - points[candidate], axis=1) <= radius
            fresh = close & (labels == -1)
            labels[fresh] = label
            pending.extend(np.flatnonzero(fresh))
        groups.append(points[labels == label])
    return groups


def hull_polygon(points: np.ndarray, margin: float = ACTIVITY_MARGIN) -> list[tuple[float, float]]:
    """Poligonul care încadrează punctele, crescut cu o marjă și ținut în cadru."""
    hull = cv2.convexHull(np.asarray(points, np.float32)).reshape(-1, 2)
    centre = hull.mean(axis=0)
    vectors = hull - centre
    lengths = np.linalg.norm(vectors, axis=1, keepdims=True)
    grown = hull + vectors / np.maximum(lengths, 1e-6) * margin
    grown = np.clip(grown, 0.0, 1.0)
    return [(round(float(x), 4), round(float(y), 4)) for x, y in grown]


def equipment_polygon(
    box: tuple[float, float, float, float],
    frame_shape: tuple[int, int],
    side_pad: float = EQUIPMENT_SIDE_PAD,
    ground_drop: float = EQUIPMENT_GROUND_DROP,
) -> list[tuple[float, float]]:
    """Cutia echipamentului, extinsă lateral și spre sol: acolo e pericolul real."""
    x1, y1, x2, y2 = box
    height = y2 - y1
    pad = (x2 - x1) * side_pad
    left = max(0.0, x1 - pad)
    right = min(1.0, x2 + pad)
    top = max(0.0, y1)
    bottom = min(1.0, y2 + height * ground_drop)
    return [(left, top), (right, top), (right, bottom), (left, bottom)]


def person_points(frames: list[np.ndarray], model, confidence: float = 0.35) -> np.ndarray:
    """Punctele de sprijin ale persoanelor, normalizate (centrul bazei cutiei)."""
    points: list[tuple[float, float]] = []
    for frame in frames:
        height, width = frame.shape[:2]
        result = model.predict(frame, classes=[0], conf=confidence, verbose=False)[0]
        if result.boxes is None:
            continue
        for x1, _, x2, y2 in result.boxes.xyxy.cpu().numpy():
            points.append((float((x1 + x2) / 2 / width), float(y2 / height)))
    return np.array(points)


def activity_proposals(
    frames: list[np.ndarray],
    camera_id: str,
    model,
    *,
    max_zones: int = 3,
    confidence: float = 0.35,
) -> list[Proposal]:
    points = person_points(frames, model, confidence)
    groups = sorted(cluster_points(points), key=len, reverse=True)[:max_zones]
    proposals = []
    for index, group in enumerate(groups, start=1):
        proposals.append(
            Proposal(
                id=f"{camera_id}-lucru-{index}",
                camera_id=camera_id,
                kind="activity",
                label=f"Zonă de lucru {index}",
                rule_type="PPE_REQUIRED",
                severity="WARNING",
                polygon=hull_polygon(group),
                score=min(1.0, len(group) / max(len(points), 1) * 2),
                evidence={"instances": int(len(group)), "frames": len(frames)},
            )
        )
    return proposals


def equipment_proposals(
    frame: np.ndarray,
    camera_id: str,
    *,
    threshold: float = 0.25,
    text_threshold: float = 0.2,
) -> list[Proposal]:
    """Open-vocabulary: cere ``transformers`` doar când e folosit."""
    try:
        import torch
        from PIL import Image
        from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor
    except ImportError as exc:  # pragma: no cover - optional extra
        raise RuntimeError("pentru zonele de echipament: uv sync --extra suggest") from exc

    model_id = "IDEA-Research/grounding-dino-tiny"
    processor = AutoProcessor.from_pretrained(model_id)
    model = AutoModelForZeroShotObjectDetection.from_pretrained(model_id).eval()
    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    inputs = processor(images=image, text=EQUIPMENT_PROMPTS, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
    results = processor.post_process_grounded_object_detection(
        outputs,
        inputs.input_ids,
        threshold=threshold,
        text_threshold=text_threshold,
        target_sizes=[image.size[::-1]],
    )[0]

    height, width = frame.shape[:2]
    proposals: list[Proposal] = []
    for box, score, label in zip(results["boxes"], results["scores"], results["labels"]):
        key = str(label).lower()
        if key not in EQUIPMENT_ZONES:
            continue
        name, rule_type, severity = EQUIPMENT_ZONES[key]
        x1, y1, x2, y2 = (float(v) for v in box)
        proposals.append(
            Proposal(
                id=f"{camera_id}-{key.replace(' ', '-')}",
                camera_id=camera_id,
                kind="equipment",
                label=name,
                rule_type=rule_type,
                severity=severity,
                polygon=equipment_polygon((x1 / width, y1 / height, x2 / width, y2 / height), (height, width)),
                score=float(score),
                evidence={"detector": "grounding-dino-tiny", "box": [round(x1), round(y1), round(x2), round(y2)]},
            )
        )
    return proposals


def read_frames(source: Path, limit: int, *, sample_every: int = 1) -> list[np.ndarray]:
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise SystemExit(f"nu pot deschide {source}")
    frames: list[np.ndarray] = []
    index = 0
    while len(frames) < limit:
        ok, frame = capture.read()
        if not ok:
            break
        if index % sample_every == 0:
            frames.append(frame)
        index += 1
    capture.release()
    if not frames:
        raise SystemExit(f"niciun cadru în {source}")
    return frames


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Propune zone dintr-un clip sau un cadru")
    parser.add_argument("--source", required=True, help="clip video sau imagine")
    parser.add_argument("--camera-id", default="stand12")
    parser.add_argument("--frames", type=int, default=60, help="câte cadre analizează pentru activitate")
    parser.add_argument("--model", default="yolo26n.pt")
    parser.add_argument("--no-equipment", action="store_true", help="doar zone de activitate (rapid)")
    parser.add_argument("--out", type=Path, help="scrie propunerile într-un JSON")
    parser.add_argument("--api-url", help="trimite propunerile la backend")
    parser.add_argument("--token", help="EDGE_TOKEN, pentru POST /zones/proposals")
    args = parser.parse_args(argv)

    source = Path(args.source)
    from ultralytics import YOLO

    detector = YOLO(args.model)
    if source.suffix.lower() in {".jpg", ".jpeg", ".png"}:
        frame = cv2.imread(str(source))
        if frame is None:
            raise SystemExit(f"nu pot citi {source}")
        frames = [frame]
    else:
        frames = read_frames(source, args.frames, sample_every=max(1, 1))

    proposals = activity_proposals(frames, args.camera_id, detector)
    if not args.no_equipment:
        try:
            proposals += equipment_proposals(frames[len(frames) // 2], args.camera_id)
        except RuntimeError as exc:
            print(f"warn: {exc}", file=sys.stderr)

    payload = {"camera_id": args.camera_id, "proposals": [p.as_dict() for p in proposals]}
    if args.out:
        args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2) if not args.out else f"scris {args.out}")

    if args.api_url:
        import httpx

        headers = {"X-Edge-Token": args.token} if args.token else {}
        response = httpx.post(f"{args.api_url.rstrip('/')}/zones/proposals", json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        print(f"trimis {len(proposals)} propuneri la {args.api_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
