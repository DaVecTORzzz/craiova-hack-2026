import asyncio
import logging
from sqlmodel import Session, select

from app.db import get_engine
from app.models import Event, EventAction, Zone
from app.schemas import EventType, Status
from app.timeutil import utcnow
from app.ws import manager

logger = logging.getLogger("safesight.escalation")

_timers: dict[str, asyncio.Task] = {}


def schedule_escalation(event_id: str, delay_s: float | None = None) -> None:
    """Start (or restart) the escalation timer for an event (7.4)."""
    with Session(get_engine()) as session:
        event = session.get(Event, event_id)
        if event is None or event.type == EventType.CAMERA_OFFLINE.value:
            return
        zone = session.get(Zone, event.zone_id)
        if zone is None or zone.escalate_after_s is None:
            return
        if delay_s is None:
            delay_s = zone.escalate_after_s

    cancel_escalation(event_id)
    _timers[event_id] = asyncio.create_task(_escalate_after(event_id, delay_s))


def cancel_escalation(event_id: str) -> None:
    task = _timers.pop(event_id, None)
    if task is not None:
        task.cancel()


def cancel_all() -> None:
    """Cancel every pending timer (app shutdown)."""
    for event_id in list(_timers):
        cancel_escalation(event_id)


async def _escalate_after(event_id: str, delay_s: float) -> None:
    await asyncio.sleep(delay_s)
    _timers.pop(event_id, None)
    await escalate(event_id)


async def escalate(event_id: str) -> None:
    """Escalate the event only if it is still open."""
    # Imported here: app.services.events imports this module.
    from app.services.events import event_out

    with Session(get_engine()) as session:
        event = session.get(Event, event_id)
        if event is None or event.status != Status.open.value:
            return

        now = utcnow()
        event.status = Status.escalated.value
        event.escalated_at = now
        session.add(event)
        session.add(EventAction(event_id=event_id, action="escalate", operator="system", at=now))
        session.commit()
        session.refresh(event)
        out = event_out(session, event)

    logger.info(f"escalate event_id={event_id}")
    await manager.broadcast("event.updated", out.model_dump(mode="json"))

    # step 9: send_slack(slack_text(out, escalated=True))


async def recover_timers() -> None:
    """At startup: re-arm timers for open events, escalate the overdue ones."""
    with Session(get_engine()) as session:
        rows = session.exec(
            select(Event, Zone)
            .join(Zone, Zone.id == Event.zone_id)
            .where(Event.status == Status.open.value)
            .where(Zone.escalate_after_s.is_not(None))  # type: ignore[union-attr]
        ).all()
        pending = [
            (event.event_id, event.type, event.received_at, zone.escalate_after_s)
            for event, zone in rows
        ]

    now = utcnow()
    for event_id, event_type, received_at, escalate_after_s in pending:
        if event_type == EventType.CAMERA_OFFLINE.value:
            continue
        remaining = (received_at - now).total_seconds() + escalate_after_s
        if remaining <= 0:
            await escalate(event_id)
        else:
            schedule_escalation(event_id, delay_s=remaining)
