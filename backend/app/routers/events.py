from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.db import get_session
from app.models import Event
from app.schemas import EventOut, OperatorActionIn
from app.services.events import apply_action, event_out
from app.services.report import generate_and_store_report

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventOut])
async def list_events(
    status: str | None = None,
    severity: str | None = None,
    camera_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    session: Session = Depends(get_session),
) -> list[EventOut]:
    query = select(Event)
    if status is not None:
        query = query.where(Event.status == status)
    if severity is not None:
        query = query.where(Event.severity == severity)
    if camera_id is not None:
        query = query.where(Event.camera_id == camera_id)

    query = query.order_by(Event.detected_at.desc()).limit(limit)
    events = session.exec(query).all()
    return [event_out(session, ev) for ev in events]


@router.get("/{event_id}", response_model=EventOut)
async def get_event(
    event_id: str,
    session: Session = Depends(get_session),
) -> EventOut:
    event = session.get(Event, event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="event not found",
        )
    return event_out(session, event)


@router.post("/{event_id}/ack", response_model=EventOut)
async def ack_event(
    event_id: str,
    body: OperatorActionIn,
    session: Session = Depends(get_session),
) -> EventOut:
    return await apply_action(session, event_id, "ack", body)


@router.post("/{event_id}/false-positive", response_model=EventOut)
async def false_positive_event(
    event_id: str,
    body: OperatorActionIn,
    session: Session = Depends(get_session),
) -> EventOut:
    return await apply_action(session, event_id, "false_positive", body)


@router.post("/{event_id}/reopen", response_model=EventOut)
async def reopen_event(
    event_id: str,
    body: OperatorActionIn,
    session: Session = Depends(get_session),
) -> EventOut:
    return await apply_action(session, event_id, "reopen", body)


@router.post("/{event_id}/regenerate-report", response_model=EventOut)
async def regenerate_report(
    event_id: str,
    session: Session = Depends(get_session),
) -> EventOut:
    event = session.get(Event, event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="event not found",
        )
    await generate_and_store_report(event_id)
    session.refresh(event)
    return event_out(session, event)
