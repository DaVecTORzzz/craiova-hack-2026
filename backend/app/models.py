from datetime import datetime
from sqlalchemy import Column, JSON, UniqueConstraint
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


class EdgeHeartbeat(SQLModel, table=True):
    """Last sign of life per camera, plus the outage incident it belongs to."""

    __tablename__ = "edge_heartbeat"
    camera_id: str = Field(primary_key=True)
    last_seen_at: datetime
    source: str = "edge"                 # edge | assumed (grace at startup)
    outage_event_id: str | None = None   # one incident per outage


class CameraOutage(SQLModel, table=True):
    """A window in which a camera was blind. Coverage is computed from this table."""

    __tablename__ = "camera_outages"
    id: int | None = Field(default=None, primary_key=True)
    camera_id: str = Field(index=True)
    event_id: str
    started_at: datetime = Field(index=True)
    ended_at: datetime | None = None


class ShiftSummary(SQLModel, table=True):
    """The generated shift summary, reused while the numbers behind it are unchanged."""

    __tablename__ = "shift_summaries"
    id: str = Field(primary_key=True)     # "<shift>:<date>"
    numbers_hash: str
    summary: str
    source: str                           # llm | template
    generated_at: datetime


class NotificationOutbox(SQLModel, table=True):
    """A notification waiting to be sent, with retry.

    The text is rendered at enqueue time, so a retry 30 s later sends exactly
    the original message with the original time. ``(event_id, kind)`` is unique:
    a restart cannot duplicate alerts. A ``failed`` row stays in the table on
    purpose — it is the record that the alert never left.
    """

    __tablename__ = "notification_outbox"
    __table_args__ = (UniqueConstraint("event_id", "kind", name="uq_notification_outbox_event_kind"),)

    id: int | None = Field(default=None, primary_key=True)
    event_id: str = Field(index=True)
    kind: str = "new"                                    # new | escalation | recovery
    channel: str = "slack"
    text: str
    status: str = Field(default="pending", index=True)   # pending | sent | failed | cancelled
    attempts: int = 0
    next_attempt_at: datetime = Field(index=True)
    last_error: str | None = None
    created_at: datetime
    sent_at: datetime | None = None
