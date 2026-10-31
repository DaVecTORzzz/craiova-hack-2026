import logging
from datetime import datetime
import httpx
from sqlmodel import Session

from app.config import get_settings
from app.db import get_engine
from app.models import Event, Zone
from app.schemas import EventOut
from app.timeutil import local_hms, to_naive_utc, utcnow
from app.ws import manager

logger = logging.getLogger("safesight.notify")


async def send_slack(text: str) -> bool:
    """POST {"text": text} to the Slack webhook. Never raises."""
    url = get_settings().slack_webhook_url
    if not url:
        logger.info(f"notification simulated: {text}")
        return False
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            res = await client.post(url, json={"text": text})
    except Exception as e:
        logger.warning(f"slack request failed: {type(e).__name__}")
        return False
    if 200 <= res.status_code < 300:
        return True
    logger.warning(f"slack returned status {res.status_code}")
    return False


def _default_slack_text(event: EventOut, escalated: bool) -> str:
    settings = get_settings()
    detected = to_naive_utc(datetime.fromisoformat(event.detected_at))
    text = (
        f"[{event.severity.value}] {event.type.value} · {event.camera_id} / {event.zone_id} · "
        f"{local_hms(detected)} · {settings.app_base_url}/incidents/{event.event_id}"
    )
    if escalated:
        with Session(get_engine()) as session:
            zone = session.get(Zone, event.zone_id)
            escalate_after_s = zone.escalate_after_s if zone is not None else None
        text = f"ESCALADARE · neconfirmat de {escalate_after_s} s · " + text
    return text


def _escalate_after_s(zone_id: str) -> int | None:
    with Session(get_engine()) as session:
        zone = session.get(Zone, zone_id)
    return zone.escalate_after_s if zone is not None else None


def slack_text(event: EventOut, escalated: bool) -> str:
    """Use automation.report.slack_text when present, else the default template."""
    try:
        import automation.report as d

        custom = getattr(d, "slack_text", None)
        if custom is not None:
            payload = event.model_dump(mode="json")
            payload["link"] = f"{get_settings().app_base_url}/incidents/{event.event_id}"
            if escalated:
                payload["escalate_after_s"] = _escalate_after_s(event.zone_id)
            return custom(payload, escalated)
    except Exception as e:
        logger.debug(f"automation slack_text unavailable: {type(e).__name__}")
    return _default_slack_text(event, escalated)


async def notify_new_event(event_id: str) -> None:
    # Imported here: app.services.events imports this module.
    from app.services.events import event_out

    with Session(get_engine()) as session:
        event = session.get(Event, event_id)
        if event is None:
            return
        out = event_out(session, event)

    if not await send_slack(slack_text(out, escalated=False)):
        return

    with Session(get_engine()) as session:
        event = session.get(Event, event_id)
        if event is None:
            return
        event.notified_at = utcnow()
        session.add(event)
        session.commit()
        session.refresh(event)
        out = event_out(session, event)
        latency_ms = int((event.notified_at - event.detected_at).total_seconds() * 1000)

    logger.info(f"notified event_id={event_id} detection_to_alert_ms={latency_ms}")
    await manager.broadcast("event.updated", out.model_dump(mode="json"))
