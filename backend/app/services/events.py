import logging
from fastapi import HTTPException, status
from sqlmodel import Session

from app.models import Camera, Event, EventAction, ReportText, Zone
from app.schemas import (
    Confidence,
    Context,
    EdgeEventIn,
    EventOut,
    EventType,
    OperatorActionIn,
    ReportOut,
    Status,
    Temporal,
)
from app.timeutil import iso, to_naive_utc, utcnow
from app.ws import manager

logger = logging.getLogger("safesight.events")


def event_out(session: Session, event: Event) -> EventOut:
    """One function to serialize an Event to EventOut everywhere (REST & WS)."""
    report_record = session.get(ReportText, event.event_id)
    report = None
    if report_record is not None:
        report = ReportOut(
            what=report_record.what,
            where=report_record.where,
            when=report_record.when,
            severity_reason=report_record.severity_reason,
            recommended_action=report_record.recommended_action,
            source=report_record.source,  # type: ignore[arg-type]
        )

    return EventOut(
        event_id=event.event_id,
        type=EventType(event.type),
        severity=event.severity,  # type: ignore[arg-type]
        status=Status(event.status),
        camera_id=event.camera_id,
        zone_id=event.zone_id,
        track_id=event.track_id,
        confidence=Confidence(
            detector=event.confidence_detector,
            temporal=Temporal(
                seen=event.confidence_temporal_seen,
                window=event.confidence_temporal_window,
            ),
        ),
        duration_s=event.duration_s,
        context=Context(**event.context),
        snapshot_url=event.snapshot_url,
        model=event.model,
        detected_at=iso(event.detected_at) or "",
        received_at=iso(event.received_at) or "",
        notified_at=iso(event.notified_at),
        escalated_at=iso(event.escalated_at),
        acked_at=iso(event.acked_at),
        acked_by=event.acked_by,
        report=report,
    )


async def ingest(session: Session, payload: EdgeEventIn) -> tuple[EventOut, bool]:
    """Ingest an event from edge (POST /edge/events). Returns (EventOut, was_created)."""
    # 3. Camera and zone validation
    camera = session.get(Camera, payload.camera_id)
    if camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="unknown camera_id",
        )

    if payload.type != EventType.CAMERA_OFFLINE:
        zone = session.get(Zone, payload.zone_id)
        if zone is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="unknown zone_id",
            )

    # 4. Idempotency check
    existing = session.get(Event, payload.event_id)
    if existing is not None:
        return event_out(session, existing), False

    # 5. Insert new event
    now = utcnow()
    detected_utc = to_naive_utc(payload.detected_at)

    event = Event(
        event_id=payload.event_id,
        type=payload.type.value,
        severity=payload.severity.value,
        status=Status.open.value,
        camera_id=payload.camera_id,
        zone_id=payload.zone_id,
        track_id=payload.track_id,
        confidence_detector=payload.confidence.detector,
        confidence_temporal_seen=payload.confidence.temporal.seen,
        confidence_temporal_window=payload.confidence.temporal.window,
        duration_s=payload.duration_s,
        context=payload.context.model_dump(),
        snapshot_url=payload.snapshot_url,
        model=payload.model,
        detected_at=detected_utc,
        received_at=now,
        notified_at=None,
        escalated_at=None,
        acked_at=None,
        acked_by=None,
    )
    session.add(event)

    # 5.1 Update camera online status
    if payload.type == EventType.CAMERA_OFFLINE:
        camera.online = False
    else:
        camera.online = True
    camera.updated_at = now
    session.add(camera)

    # 5.2 Commit
    session.commit()
    session.refresh(event)
    out = event_out(session, event)

    # 5.3 Broadcast event.created
    await manager.broadcast("event.created", out.model_dump(mode="json"))

    # 5.4 Notify new event via Slack
    # step 9: asyncio.create_task(notify_new_event(event_id))

    # 5.5 Generate and store report
    # step 10: asyncio.create_task(generate_and_store_report(event_id))

    # 5.6 Schedule escalation timer
    # step 8: schedule_escalation(event_id)

    # 6. Log one line
    latency_ms = int((now - detected_utc).total_seconds() * 1000)
    logger.info(f"ingest event_id={event.event_id} type={event.type} ingest_latency_ms={latency_ms}")

    # 7. Return (EventOut, True)
    return out, True


# 7.3: action -> (allowed from, new status)
ACTIONS: dict[str, tuple[set[Status], Status]] = {
    "ack": ({Status.open, Status.escalated}, Status.acknowledged),
    "false_positive": ({Status.open, Status.escalated, Status.acknowledged}, Status.false_positive),
    "reopen": ({Status.acknowledged, Status.false_positive, Status.escalated, Status.resolved}, Status.open),
}


async def apply_action(session: Session, event_id: str, action: str, body: OperatorActionIn) -> EventOut:
    """Operator action on an event (7.3). action is one of ack | false_positive | reopen."""
    event = session.get(Event, event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="event not found",
        )

    allowed_from, new_status = ACTIONS[action]
    if Status(event.status) not in allowed_from:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"cannot {action} an event with status {event.status}",
        )

    now = utcnow()
    event.status = new_status.value
    note = None
    if action == "ack":
        event.acked_at = now
        event.acked_by = body.operator
        # step 8: cancel_escalation(event_id)
    elif action == "false_positive":
        note = body.note
        # step 8: cancel_escalation(event_id)
    elif action == "reopen":
        event.acked_at = None
        event.acked_by = None
        event.escalated_at = None
        # step 8: schedule_escalation(event_id)

    session.add(event)
    session.add(EventAction(event_id=event_id, action=action, operator=body.operator, at=now, note=note))
    session.commit()
    session.refresh(event)
    out = event_out(session, event)

    await manager.broadcast("event.updated", out.model_dump(mode="json"))
    return out
