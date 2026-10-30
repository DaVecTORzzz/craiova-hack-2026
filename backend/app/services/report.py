import asyncio
import logging
from datetime import datetime
from sqlmodel import Session

from app.db import get_engine
from app.models import Event, ReportText
from app.schemas import EventOut, EventType, ReportOut
from app.timeutil import local_hms, to_naive_utc, utcnow
from app.ws import manager

logger = logging.getLogger("safesight.report")

# type -> (what, severity_reason, recommended_action), VERBATIM from the plan (7.6)
TEMPLATES: dict[EventType, tuple[str, str, str]] = {
    EventType.RESTRICTED_ZONE: (
        "Persoană în zona {zone_id}.",
        "Zonă restricționată activă; risc de accident.",
        "Oprește activitatea în zonă și contactează persoana prin radio.",
    ),
    EventType.NO_PPE: (
        "Echipament de protecție lipsă în zona {zone_id}.",
        "Lucru fără echipamentul obligatoriu.",
        "Supervizorul verifică echipamentul persoanei înainte de reluarea lucrului.",
    ),
    EventType.FOD: (
        "Obiect static pe suprafața {zone_id}.",
        "Obiectele uitate pot fi aspirate de motoare.",
        "Inspectează și îndepărtează obiectul înainte de următoarea mișcare.",
    ),
    EventType.SMOKING: (
        "Posibil fumat în zona {zone_id}.",
        "Fumatul lângă aeronave și combustibil e interzis.",
        "Supervizorul verifică imediat situația la fața locului.",
    ),
    EventType.CAMERA_OFFLINE: (
        "Camera {camera_id} nu mai transmite cadre.",
        "Zona nu mai e supravegheată.",
        "Verifică alimentarea și rețeaua camerei.",
    ),
}


def template_report(event: EventOut) -> ReportOut:
    what, severity_reason, recommended_action = TEMPLATES[event.type]
    detected = to_naive_utc(datetime.fromisoformat(event.detected_at))
    return ReportOut(
        what=what.format(zone_id=event.zone_id, camera_id=event.camera_id),
        where=f"Camera {event.camera_id}, zona {event.zone_id}.",
        when=f"{local_hms(detected)}, timp în zonă {event.duration_s:.1f} s.",
        severity_reason=severity_reason,
        recommended_action=recommended_action,
        source="template",
    )


async def build_report(event: EventOut) -> ReportOut:
    """Dalina's automation.report.generate with a 3 s budget; template on any failure."""
    try:
        import automation.report as d

        result = await asyncio.wait_for(asyncio.to_thread(d.generate, event.model_dump()), timeout=3.0)
        return ReportOut.model_validate(result)
    except Exception as e:
        logger.info(f"report fallback to template event_id={event.event_id} reason={type(e).__name__}")
        return template_report(event)


async def generate_and_store_report(event_id: str) -> None:
    # Imported here: app.services.events imports this module.
    from app.services.events import event_out

    with Session(get_engine()) as session:
        event = session.get(Event, event_id)
        if event is None:
            return
        out = event_out(session, event)

    report = await build_report(out)

    with Session(get_engine()) as session:
        event = session.get(Event, event_id)
        if event is None:
            return
        record = session.get(ReportText, event_id)
        if record is None:
            record = ReportText(event_id=event_id, generated_at=utcnow(), **report.model_dump())
        else:
            for field, value in report.model_dump().items():
                setattr(record, field, value)
            record.generated_at = utcnow()
        session.add(record)
        session.commit()
        out = event_out(session, event)

    await manager.broadcast("event.updated", out.model_dump(mode="json"))
