"""Demo fallback: send one edge event to a running API on demand.

Use it when the edge, the camera or the model fails during the demo. It goes
through the same HTTP routes as the edge (POST /edge/snapshots, then
POST /edge/events), so Live, the incident page, Slack and escalation behave
exactly as with a real detection.

    cd backend
    uv run python scripts/demo_event.py                      # RESTRICTED_ZONE on stand12/engine-left
    uv run python scripts/demo_event.py --type FOD
    uv run python scripts/demo_event.py --snapshot frame.jpg   # an already-blurred JPEG only
"""

import argparse
import io
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from PIL import Image, ImageDraw

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.mock import TEMPLATES  # noqa: E402
from app.schemas import EdgeEventIn, EventType  # noqa: E402

TEMPLATES_BY_TYPE = {tpl["type"].value: tpl for tpl in TEMPLATES}


def placeholder_jpeg(text: str) -> bytes:
    """Synthetic frame: no people, nothing to blur."""
    image = Image.new("RGB", (640, 360), "#3A3A3A")
    ImageDraw.Draw(image).text((16, 16), text, fill="#FFFFFF")
    buf = io.BytesIO()
    image.save(buf, format="JPEG")
    return buf.getvalue()


def build_payload(event_type: str, snapshot_url: str, event_id: str, track_id: int, engine_on: bool) -> dict:
    tpl = TEMPLATES_BY_TYPE[event_type]
    payload = {
        "event_id": event_id,
        "type": event_type,
        "severity": tpl["severity"].value,
        "camera_id": tpl["camera_id"],
        "zone_id": tpl["zone_id"],
        "track_id": track_id,
        "confidence": {"detector": 0.91, "temporal": {"seen": 14, "window": 15}},
        "duration_s": 3.0 if event_type == EventType.FOD.value else 1.4,
        "context": {"engine_on": engine_on},
        "snapshot_url": snapshot_url,
        "model": tpl["model"],
        "detected_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
    }
    # Fail here, before the demo audience sees a 422.
    EdgeEventIn.model_validate(payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Send one demo edge event to the SafeSight API.")
    parser.add_argument("--type", default=EventType.RESTRICTED_ZONE.value, choices=sorted(TEMPLATES_BY_TYPE))
    parser.add_argument("--api-url", default=os.getenv("API_URL", "http://localhost:8000"))
    parser.add_argument("--edge-token", default=os.getenv("EDGE_TOKEN", "dev-edge-token"))
    parser.add_argument("--snapshot", type=Path, help="JPEG to upload; must already be blurred")
    parser.add_argument("--no-engine", action="store_true", help="do not turn the camera engine on first")
    args = parser.parse_args(argv)

    tpl = TEMPLATES_BY_TYPE[args.type]
    camera_id = tpl["camera_id"]
    track_id = 0 if args.type == EventType.FOD.value else random.randint(1, 99)
    event_id = f"evt_{camera_id}_{int(time.time() * 1000)}_{track_id}"
    headers = {"X-Edge-Token": args.edge_token}
    engine_on = args.type == EventType.RESTRICTED_ZONE.value and not args.no_engine

    with httpx.Client(base_url=args.api_url.rstrip("/"), timeout=5) as client:
        # Only the restricted-zone demo needs the engine on; FOD/NO_PPE do not.
        if engine_on:
            client.put(f"/cameras/{camera_id}/engine", json={"on": True}).raise_for_status()

        if args.snapshot:
            print("warning: --snapshot is uploaded as-is; only pass an already-blurred JPEG", file=sys.stderr)
        jpeg = args.snapshot.read_bytes() if args.snapshot else placeholder_jpeg(f"DEMO {args.type} {camera_id}")
        res = client.post(
            "/edge/snapshots",
            headers=headers,
            data={"event_id": event_id},
            files={"file": (f"{event_id}.jpg", jpeg, "image/jpeg")},
        )
        res.raise_for_status()
        snapshot_url = res.json()["snapshot_url"]

        res = client.post("/edge/events", headers=headers, json=build_payload(args.type, snapshot_url, event_id, track_id, engine_on))
        if res.status_code not in (200, 201):
            print(f"error {res.status_code}: {res.text}", file=sys.stderr)
            return 1

    print(f"{res.status_code} {args.type} {event_id}")
    print(f"snapshot: {snapshot_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
