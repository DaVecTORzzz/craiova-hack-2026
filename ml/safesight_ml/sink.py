"""Event sinks: local JSONL for the first slice, HTTP for integration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

import cv2
import httpx
import numpy as np

from .events import EdgeEvent


class Sink(Protocol):
    def store_snapshot(self, event_id: str, frame: np.ndarray) -> str: ...

    def emit(self, event: EdgeEvent) -> None: ...


class JsonlSink:
    """Dry-run sink: writes JPEG snapshots and one JSON event per line."""

    def __init__(self, out_dir: str | Path) -> None:
        self.out_dir = Path(out_dir)
        self.snapshots_dir = self.out_dir / "snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.events_path = self.out_dir / "events.jsonl"
        self.events_path.write_text("", encoding="utf-8")

    def store_snapshot(self, event_id: str, frame: np.ndarray) -> str:
        path = self.snapshots_dir / f"{event_id}.jpg"
        if not cv2.imwrite(str(path), frame):
            raise OSError(f"could not write snapshot to {path}")
        return f"/snapshots/{path.name}"

    def emit(self, event: EdgeEvent) -> None:
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(event.model_dump_json() + "\n")


class HttpSink:
    """Integration sink: POST /edge/snapshots, then POST /edge/events."""

    def __init__(
        self,
        api_url: str,
        edge_token: str,
        *,
        client: httpx.Client | None = None,
        timeout: float = 5.0,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.edge_token = edge_token
        self._client = client or httpx.Client(timeout=timeout)

    @property
    def headers(self) -> dict[str, str]:
        return {"X-Edge-Token": self.edge_token}

    def store_snapshot(self, event_id: str, frame: np.ndarray) -> str:
        ok, encoded = cv2.imencode(".jpg", frame)
        if not ok:
            raise OSError("could not encode snapshot as JPEG")
        response = self._client.post(
            f"{self.api_url}/edge/snapshots",
            headers=self.headers,
            data={"event_id": event_id},
            files={"file": (f"{event_id}.jpg", encoded.tobytes(), "image/jpeg")},
        )
        response.raise_for_status()
        payload = response.json()
        snapshot_url = payload.get("snapshot_url")
        if not isinstance(snapshot_url, str) or not snapshot_url:
            raise ValueError("backend did not return snapshot_url")
        return snapshot_url

    def emit(self, event: EdgeEvent) -> None:
        response = self._client.post(
            f"{self.api_url}/edge/events",
            headers=self.headers,
            json=json.loads(event.model_dump_json()),
        )
        response.raise_for_status()

    def upload_reference(self, zone_id: str, frame: np.ndarray) -> str:
        """POST /zones/reference-frame: the image the zone editor draws on. ``frame`` must be blurred."""
        ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ok:
            raise OSError("could not encode reference frame as JPEG")
        response = self._client.post(
            f"{self.api_url}/zones/reference-frame",
            headers=self.headers,
            data={"zone_id": zone_id},
            files={"file": (f"{zone_id}.jpg", encoded.tobytes(), "image/jpeg")},
        )
        response.raise_for_status()
        return str(response.json().get("reference_frame") or "")

    def close(self) -> None:
        self._client.close()
