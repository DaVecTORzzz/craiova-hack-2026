"""Contract-valid edge event.

The source of truth is `docs/contract.md` in the public repo. Edge sends
detection fields only; `status`, `report` and the backend timestamps are not
part of this model.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

EventType = Literal[
    "RESTRICTED_ZONE",
    "NO_PPE",
    "FOD",
    "SMOKING",
    "CAMERA_OFFLINE",
    "CROWD",
]
Severity = Literal["CRITICAL", "WARNING"]

_EVENT_ID_RE = re.compile(r"^evt_[a-z0-9-]+_\d+_\d+$")


class TemporalConfidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seen: int = Field(ge=0)
    window: int = Field(ge=0)


class Confidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detector: float = Field(ge=0.0, le=1.0)
    temporal: TemporalConfidence


class EventContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine_on: bool = False


class EdgeEvent(BaseModel):
    """Payload posted to ``POST /edge/events``."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    type: EventType
    severity: Severity
    camera_id: str = Field(min_length=1)
    zone_id: str = Field(min_length=1)
    track_id: int = Field(ge=0)
    confidence: Confidence
    duration_s: float = Field(ge=0.0)
    context: EventContext
    snapshot_url: str
    model: str = Field(min_length=1)
    detected_at: datetime

    @field_validator("event_id")
    @classmethod
    def _event_id_format(cls, value: str) -> str:
        if not _EVENT_ID_RE.fullmatch(value):
            raise ValueError("event_id must match evt_<camera_id>_<unix_ms>_<track_id>")
        return value

    @field_validator("snapshot_url")
    @classmethod
    def _snapshot_is_http(cls, value: str) -> str:
        if value.startswith("minio://"):
            raise ValueError("snapshot_url must be an HTTP URL, never minio://")
        if value.startswith("/") and not value.startswith("/snapshots/"):
            raise ValueError("root-relative snapshot_url must start with /snapshots/")
        if not value.startswith(("/snapshots/", "http://", "https://")):
            raise ValueError("snapshot_url must be /snapshots/... or an HTTP URL")
        return value

    @field_validator("detected_at")
    @classmethod
    def _detected_at_has_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("detected_at must be timezone-aware")
        return value.astimezone(UTC)

    @field_serializer("detected_at")
    def _serialize_detected_at(self, value: datetime) -> str:
        return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    def to_jsonl(self) -> str:
        return self.model_dump_json()
