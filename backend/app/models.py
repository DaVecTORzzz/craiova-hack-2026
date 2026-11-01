from datetime import datetime
from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class Camera(SQLModel, table=True):
    __tablename__ = "cameras"
    id: str = Field(primary_key=True)
    name: str
    rtsp_url: str
    engine_on: bool = False
    online: bool = True
    updated_at: datetime


class Zone(SQLModel, table=True):
    __tablename__ = "zones"
    id: str = Field(primary_key=True)
    camera_id: str = Field(foreign_key="cameras.id", index=True)
    name: str
    rule_type: str
    active_when: str
    required_ppe: list = Field(default_factory=list, sa_column=Column(JSON))
    severity: str
    debounce_s: float
    notify_channel: str = "slack"
    escalate_after_s: int | None = None
    polygon: list = Field(sa_column=Column(JSON))
    reference_frame: str | None = None


class Event(SQLModel, table=True):
    __tablename__ = "events"
    event_id: str = Field(primary_key=True)
    type: str
    severity: str
    status: str = Field(index=True)
    camera_id: str = Field(index=True)
    zone_id: str
    track_id: int
    confidence_detector: float
    confidence_temporal_seen: int
    confidence_temporal_window: int
    duration_s: float
    context: dict = Field(sa_column=Column(JSON))
    snapshot_url: str
    model: str
    detected_at: datetime = Field(index=True)
    received_at: datetime
    notified_at: datetime | None = None
    escalated_at: datetime | None = None
    acked_at: datetime | None = None
    acked_by: str | None = None


class EventAction(SQLModel, table=True):
    __tablename__ = "event_actions"
    id: int | None = Field(default=None, primary_key=True)
    event_id: str = Field(foreign_key="events.event_id", index=True)
    action: str          # ack | false_positive | reopen | escalate
    operator: str        # operator name, or "system" for escalate
    at: datetime
    note: str | None = None


class ReportText(SQLModel, table=True):
    __tablename__ = "report_texts"
    event_id: str = Field(primary_key=True, foreign_key="events.event_id")
    what: str
    where: str
    when: str
    severity_reason: str
    recommended_action: str
    source: str          # llm | template
    generated_at: datetime


class Snapshot(SQLModel, table=True):
    __tablename__ = "snapshots"
    file_name: str = Field(primary_key=True)
    path: str
    created_at: datetime
    expires_at: datetime


class ConfigState(SQLModel, table=True):
    """Single row (id=1). config_version goes up on every zone or engine change."""
    __tablename__ = "config_state"
    id: int = Field(default=1, primary_key=True)
    config_version: int = 1


class ZoneProposal(SQLModel, table=True):
    """O zonă propusă de analiza vizuală, înainte ca un operator să o accepte."""

    __tablename__ = "zone_proposals"
    id: str = Field(primary_key=True)
    camera_id: str = Field(index=True)
    kind: str  # activity | equipment
    label: str
    rule_type: str
    severity: str
    polygon: list = Field(sa_column=Column(JSON))
    score: float = 0.0
    evidence: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime
