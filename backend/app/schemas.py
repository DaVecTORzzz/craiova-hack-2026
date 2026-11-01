from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from app.geometry import crossing_edges


class EventType(str, Enum):
    RESTRICTED_ZONE = "RESTRICTED_ZONE"
    NO_PPE = "NO_PPE"
    FOD = "FOD"
    SMOKING = "SMOKING"
    CAMERA_OFFLINE = "CAMERA_OFFLINE"
    # CROWD is reserved in the contract and NOT accepted yet.


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"


class Status(str, Enum):
    open = "open"
    acknowledged = "acknowledged"
    false_positive = "false_positive"
    escalated = "escalated"
    resolved = "resolved"


class RuleType(str, Enum):
    RESTRICTED = "RESTRICTED"
    PPE_REQUIRED = "PPE_REQUIRED"
    FOD_WATCH = "FOD_WATCH"
    NO_SMOKING = "NO_SMOKING"


class ActiveWhen(str, Enum):
    always = "always"
    engine_on = "engine_on"


class Temporal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seen: int = Field(ge=0)
    window: int = Field(ge=1)


class Confidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    detector: float = Field(ge=0, le=1)
    temporal: Temporal


class Context(BaseModel):
    model_config = ConfigDict(extra="forbid")
    engine_on: bool


EVENT_ID_PATTERN = r"^evt_[a-z0-9-]+_\d{13}_\d+$"


class EdgeEventIn(BaseModel):
    """What A sends to POST /edge/events. Anything else -> 422."""
    model_config = ConfigDict(extra="forbid")
    event_id: str = Field(pattern=EVENT_ID_PATTERN, max_length=120)
    type: EventType
    severity: Severity
    camera_id: str = Field(min_length=1, max_length=64)
    zone_id: str = Field(min_length=1, max_length=64)
    track_id: int = Field(ge=0)
    confidence: Confidence
    duration_s: float = Field(ge=0)
    context: Context
    snapshot_url: str = Field(min_length=1, max_length=300)
    model: str = Field(min_length=1, max_length=64)
    detected_at: AwareDatetime

    @field_validator("snapshot_url")
    @classmethod
    def validate_snapshot_url(cls, v: str) -> str:
        if v.startswith("minio://"):
            raise ValueError("snapshot_url must be an HTTP URL, never minio://")
        if v.startswith("/") and not v.startswith("/snapshots/"):
            raise ValueError("root-relative snapshot_url must start with /snapshots/")
        if not v.startswith(("/snapshots/", "http://", "https://")):
            raise ValueError("snapshot_url must be /snapshots/... or an HTTP URL")
        return v


class ReportOut(BaseModel):
    what: str
    where: str
    when: str
    severity_reason: str
    recommended_action: str
    source: Literal["llm", "template"]


class EventOut(BaseModel):
    """What B returns everywhere (REST and WebSocket)."""
    event_id: str
    type: EventType
    severity: Severity
    status: Status
    camera_id: str
    zone_id: str
    track_id: int
    confidence: Confidence
    duration_s: float
    context: Context
    snapshot_url: str
    model: str
    detected_at: str
    received_at: str
    notified_at: str | None
    escalated_at: str | None
    acked_at: str | None
    acked_by: str | None
    report: ReportOut | None


class OperatorActionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operator: str = Field(min_length=1, max_length=64)
    note: str | None = Field(default=None, max_length=500)


class EngineIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    on: bool


class CameraOut(BaseModel):
    id: str
    name: str
    rtsp_url: str
    online: bool
    engine_on: bool


class ZoneIO(BaseModel):
    """Same shape for GET and PUT /zones."""
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")
    camera_id: str
    name: str = Field(min_length=1, max_length=80)
    rule_type: RuleType
    active_when: ActiveWhen
    required_ppe: list[str] = Field(default_factory=list)
    severity: Severity
    debounce_s: float = Field(ge=0)
    escalate_after_s: int | None = Field(default=None, ge=1)
    notify_channel: Literal["slack"]
    polygon: list[tuple[float, float]] = Field(min_length=3)
    reference_frame: str | None = None

    @field_validator("polygon")
    @classmethod
    def validate_polygon(cls, v: list[tuple[float, float]]) -> list[tuple[float, float]]:
        for point in v:
            x, y = point
            if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
                raise ValueError("polygon coordinates must be normalized 0-1")
        return v


class ZoneIn(ZoneIO):
    """PUT /zones body: also rejects a polygon whose edges cross (an hourglass, not a perimeter).

    Only on input: zones already stored are still returned as they are.
    """

    @field_validator("polygon")
    @classmethod
    def validate_polygon_is_simple(cls, v: list[tuple[float, float]]) -> list[tuple[float, float]]:
        crossing = crossing_edges(v)
        if crossing:
            edges = ", ".join(str(i) for i in sorted(crossing))
            raise ValueError(f"polygon edges cross each other (edges {edges}); points must follow the outline")
        return v


class EdgeZonesOut(BaseModel):
    camera_id: str
    engine_on: bool
    config_version: int
    zones: list[ZoneIO]


class Kpi(BaseModel):
    ppe_compliance: float | None
    open_incidents: int
    avg_detection_to_alert_s: float | None
    escalated: int


class ShiftReport(BaseModel):
    shift: Literal["morning", "afternoon", "night"]
    date: str
    kpi: Kpi
    avg_ack_s: int | None
    summary: str
    by_type: list[dict]
    by_zone: list[dict]
    by_hour: list[dict]


class ZoneProposalIO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=80)
    camera_id: str
    kind: Literal["activity", "equipment"]
    label: str = Field(min_length=1, max_length=80)
    rule_type: RuleType
    severity: Severity
    polygon: list[tuple[float, float]] = Field(min_length=3)
    score: float = 0.0
    evidence: dict = Field(default_factory=dict)
    created_at: datetime | None = None


class ZoneProposalsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    camera_id: str
    proposals: list[ZoneProposalIO]
