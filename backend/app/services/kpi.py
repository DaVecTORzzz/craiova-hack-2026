import asyncio
import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal
from sqlmodel import Session, select

from app.config import get_settings
from app.models import Event
from app.schemas import EventType, Kpi, Severity, ShiftReport, Status
from app.timeutil import LOCAL_TZ, to_naive_utc

logger = logging.getLogger("safesight.kpi")

Shift = Literal["morning", "afternoon", "night"]

# shift -> local start hour; every shift lasts 8 h (night ends the next day)
SHIFT_LABELS: dict[str, str] = {"morning": "de dimineață", "afternoon": "de după-amiază", "night": "de noapte"}
SHIFT_START: dict[str, int] = {"morning": 6, "afternoon": 14, "night": 22}


def shift_window(shift: Shift, day: date) -> tuple[datetime, datetime]:
    """Local shift window as naive UTC [start, end)."""
    start_local = datetime.combine(day, time(SHIFT_START[shift]), tzinfo=LOCAL_TZ)
    end_local = start_local + timedelta(hours=8)
    return to_naive_utc(start_local), to_naive_utc(end_local)


def current_shift(now_local: datetime | None = None) -> tuple[Shift, date]:
    """The shift that contains now (local time)."""
    now_local = now_local or datetime.now(LOCAL_TZ)
    hour = now_local.hour
    if 6 <= hour < 14:
        return "morning", now_local.date()
    if 14 <= hour < 22:
        return "afternoon", now_local.date()
    if hour >= 22:
        return "night", now_local.date()
    return "night", now_local.date() - timedelta(days=1)


def events_in_window(session: Session, shift: Shift, day: date) -> list[Event]:
    start, end = shift_window(shift, day)
    query = select(Event).where(Event.detected_at >= start).where(Event.detected_at < end)
    return list(session.exec(query).all())


def _incidents(events: list[Event]) -> list[Event]:
    """A false positive is not an incident: it must not inflate the report."""
    return [event for event in events if event.status != Status.false_positive.value]


def _false_positives(events: list[Event]) -> list[Event]:
    return [event for event in events if event.status == Status.false_positive.value]


def compute_kpi(events: list[Event]) -> Kpi:
    incidents = _incidents(events)
    open_incidents = sum(1 for e in incidents if e.status in (Status.open.value, Status.escalated.value))
    escalated = sum(1 for e in incidents if e.escalated_at is not None)

    alert_delays = [(e.notified_at - e.detected_at).total_seconds() for e in incidents if e.notified_at is not None]
    avg_alert = round(sum(alert_delays) / len(alert_delays), 1) if alert_delays else None

    # See OPEN QUESTION Q3.
    observations = get_settings().ppe_observations_per_shift
    ppe_compliance = None
    if observations > 0:
        valid_no_ppe = sum(1 for e in incidents if e.type == EventType.NO_PPE.value)
        ppe_compliance = round(min(1.0, max(0.0, 1 - valid_no_ppe / observations)), 2)

    confirmed = sum(1 for e in incidents if e.status in (Status.acknowledged.value, Status.resolved.value))
    resolution_rate = round(confirmed / len(incidents), 2) if incidents else None
    alerted = sum(1 for e in incidents if e.notified_at is not None)

    return Kpi(
        ppe_compliance=ppe_compliance,
        open_incidents=open_incidents,
        avg_detection_to_alert_s=avg_alert,
        escalated=escalated,
        resolution_rate=resolution_rate,
        alerted_incidents=alerted,
    )


def _avg_ack_s(events: list[Event]) -> int | None:
    delays = [(e.acked_at - e.detected_at).total_seconds() for e in events if e.acked_at is not None]
    return round(sum(delays) / len(delays)) if delays else None


def _severity_counts(events: list[Event]) -> dict[str, int]:
    return {
        "critical": sum(1 for e in events if e.severity == Severity.CRITICAL.value),
        "warning": sum(1 for e in events if e.severity == Severity.WARNING.value),
    }


def _shift_hours(shift: Shift) -> list[str]:
    """The 8 local hours of the shift, in shift order (night: 22, 23, 00..05)."""
    start = SHIFT_START[shift]
    return [f"{(start + offset) % 24:02d}" for offset in range(8)]


def _hourly_counts(events: list[Event], shift: Shift) -> list[dict]:
    hours = _shift_hours(shift)
    counts = {hour: 0 for hour in hours}
    for event in events:
        hour = event.detected_at.replace(tzinfo=timezone.utc).astimezone(LOCAL_TZ).strftime("%H")
        if hour in counts:
            counts[hour] += 1
    return [{"hour": hour, "count": counts[hour]} for hour in hours]


async def build_shift_report(session: Session, shift: Shift, day: date) -> ShiftReport:
    events = events_in_window(session, shift, day)
    incidents = _incidents(events)
    false_positives = _false_positives(events)
    kpi = compute_kpi(events)

    by_type = []
    for event_type in sorted({e.type for e in events}):
        group = [e for e in incidents if e.type == event_type]
        by_type.append(
            {
                "type": event_type,
                **_severity_counts(group),
                "false_positive": sum(1 for e in false_positives if e.type == event_type),
            }
        )

    by_zone = []
    for zone_id in sorted({e.zone_id for e in events}):
        group = [e for e in incidents if e.zone_id == zone_id]
        by_zone.append(
            {
                "zone_id": zone_id,
                **_severity_counts(group),
                "avg_ack_s": _avg_ack_s(group),
                "false_positive": sum(1 for e in false_positives if e.zone_id == zone_id),
            }
        )

    by_hour = _hourly_counts(incidents, shift)

    day_str = day.isoformat()
    numbers = {
        "shift": shift,
        "date": day_str,
        "kpi": kpi.model_dump(mode="json"),
        "avg_ack_s": _avg_ack_s(incidents),
        "by_type": by_type,
        "by_zone": by_zone,
        "by_hour": by_hour,
        "total_events": len(incidents),
        "false_positives": len(false_positives),
    }
    summary = await _summary(numbers, len(incidents))
    return ShiftReport(summary=summary, **numbers)


def _plural(count: int, one: str, many: str) -> str:
    return one if count == 1 else many


async def _summary(numbers: dict, n_events: int) -> str:
    try:
        import automation.report as d

        result = await asyncio.wait_for(asyncio.to_thread(d.summarize, numbers), timeout=3.0)
        if isinstance(result, str) and result.strip():
            return result
    except Exception as e:
        logger.info(f"shift summary fallback reason={type(e).__name__}")
    kpi = numbers["kpi"]
    escalated = kpi["escalated"]
    open_incidents = kpi["open_incidents"]
    return (
        f"Tura {SHIFT_LABELS.get(numbers['shift'], numbers['shift'])} din {numbers['date']}: "
        f"{n_events} {_plural(n_events, 'eveniment', 'evenimente')}, "
        f"{open_incidents} {_plural(open_incidents, 'deschis', 'deschise')}, "
        f"{escalated} {_plural(escalated, 'escaladat', 'escaladate')}."
    )
