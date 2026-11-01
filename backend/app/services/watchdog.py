"""Camera watchdog: a camera that stops reporting becomes a real incident.

The edge proves it is alive through ``POST /edge/heartbeat`` or, for edges that
already poll for their zones, through ``GET /edge/zones``. After
``camera_offline_after_s`` without a beat, the backend opens one
``CAMERA_OFFLINE`` event per outage; the first beat after that resolves it and
closes the outage window.

Why the backend and not the edge: an edge that stopped cannot report that it
stopped. See ``docs/contract.md``, "Camera offline".
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlmodel import Session, select

from app.config import get_settings
from app.db import get_engine
from app.models import Camera, CameraOutage, EdgeHeartbeat, Event, EventAction
from app.schemas import Confidence, Context, EdgeEventIn, EventOut, EventType, Severity, Status, Temporal
from app.services import outbox
from app.services.events import event_out, ingest
from app.timeutil import utcnow
from app.ws import manager

logger = logging.getLogger("safesight.watchdog")

PLACEHOLDER_SNAPSHOT = "/snapshots/placeholder.jpg"

_task: asyncio.Task | None = None
_task_loop: asyncio.AbstractEventLoop | None = None


def seed_missing_beats() -> None:
    """Grace at startup: a camera that never reported yet is not offline.

    Without this, a demo started before its edges opens one incident per camera
    in the first second, which is both wrong and loud.
    """
    now = utcnow()
    with Session(get_engine()) as session:
        for camera in session.exec(select(Camera)).all():
            if session.get(EdgeHeartbeat, camera.id) is None:
                session.add(EdgeHeartbeat(camera_id=camera.id, last_seen_at=now, source="assumed"))
        session.commit()


def _recovery_text(event: Event, now: datetime) -> str:
    minutes = max(1, round((now - event.detected_at).total_seconds() / 60))
    link = f"{get_settings().app_base_url}/incidents/{event.event_id}"
    return f"[REVENIRE] Camera {event.camera_id} transmite din nou, după {minutes} min de orbire · {link}"


async def record_beat(session: Session, camera_id: str) -> EventOut | None:
    """Register a heartbeat. Returns the recovered incident if the camera was offline.

    Raises ``KeyError`` for an unknown camera. Commits the given session: a beat
    is a write, even when the route that carries it is a read.
    """
    now = utcnow()
    camera = session.get(Camera, camera_id)
    if camera is None:
        raise KeyError(camera_id)

    beat = session.get(EdgeHeartbeat, camera_id)
    if beat is None:
        beat = EdgeHeartbeat(camera_id=camera_id, last_seen_at=now, source="edge")
    else:
        beat.last_seen_at = now
        beat.source = "edge"

    outage_id = beat.outage_event_id
    recovered: Event | None = None
    if outage_id:
        recovered = session.get(Event, outage_id)
        if recovered is not None:
            recovered.status = Status.resolved.value
            session.add(recovered)
            session.add(EventAction(event_id=outage_id, action="recovered", operator="system", at=now))
        outage = session.exec(select(CameraOutage).where(CameraOutage.event_id == outage_id)).first()
        if outage is not None:
            outage.ended_at = now
            session.add(outage)
        beat.outage_event_id = None

    camera.online = True
    camera.updated_at = now
    session.add(camera)
    session.add(beat)

    out = event_out(session, recovered) if recovered is not None else None
    if out is not None:
        outbox.enqueue(outage_id or "", "recovery", _recovery_text(recovered, now), session=session)
    session.commit()

    if out is not None:
        logger.info(f"camera recovered camera_id={camera_id} event_id={outage_id}")
        await manager.broadcast("event.updated", out.model_dump(mode="json"))
    return out


def _due_cameras(threshold_s: float, now: datetime) -> list[tuple[str, bool, datetime]]:
    with Session(get_engine()) as session:
        due: list[tuple[str, bool, datetime]] = []
        for camera in session.exec(select(Camera)).all():
            beat = session.get(EdgeHeartbeat, camera.id)
            if beat is None or beat.outage_event_id is not None:
                continue
            if (now - beat.last_seen_at).total_seconds() > threshold_s:
                due.append((camera.id, camera.engine_on, beat.last_seen_at))
        return due


async def _open_outage(camera_id: str, engine_on: bool, last_seen: datetime, now: datetime) -> None:
    event_id = f"evt_{camera_id}_{int(now.replace(tzinfo=UTC).timestamp() * 1000)}_0"
    payload = EdgeEventIn(
        event_id=event_id,
        type=EventType.CAMERA_OFFLINE,
        severity=Severity.WARNING,
        camera_id=camera_id,
        zone_id=camera_id,  # a dead camera belongs to no zone; see contract
        track_id=0,
        confidence=Confidence(detector=1.0, temporal=Temporal(seen=1, window=1)),
        duration_s=0.0,
        context=Context(engine_on=engine_on),
        snapshot_url=PLACEHOLDER_SNAPSHOT,
        model="watchdog-v1",
        detected_at=now.replace(tzinfo=UTC),
    )
    with Session(get_engine()) as session:
        beat = session.get(EdgeHeartbeat, camera_id)
        if beat is None or beat.outage_event_id is not None:
            return
        # ingest() writes the event and its alert row, commits, and broadcasts.
        await ingest(session, payload)
        beat.outage_event_id = event_id
        session.add(beat)
        session.add(CameraOutage(camera_id=camera_id, event_id=event_id, started_at=last_seen))
        session.commit()
    logger.info(f"camera offline camera_id={camera_id} event_id={event_id}")


async def tick() -> list[str]:
    """Open an outage for every camera that has been silent for too long."""
    settings = get_settings()
    # In mock mode there are no edges to hear from: silence would be the expected
    # state, and three incidents at startup are noise, not information.
    if settings.use_mock or settings.camera_offline_after_s <= 0:
        return []
    threshold = settings.camera_offline_after_s
    now = utcnow()
    opened: list[str] = []
    for camera_id, engine_on, last_seen in _due_cameras(threshold, now):
        await _open_outage(camera_id, engine_on, last_seen, now)
        opened.append(camera_id)
    return opened


async def _run() -> None:
    interval = get_settings().watchdog_interval_s
    while True:
        await asyncio.sleep(interval)
        try:
            await tick()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - the watchdog outlives one bad tick
            logger.warning(f"watchdog tick failed: {type(exc).__name__}")


def start() -> None:
    global _task, _task_loop
    loop = asyncio.get_running_loop()
    if _task is not None and not _task.done() and _task_loop is loop:
        return
    if _task is not None and _task_loop is not loop:
        _task.cancel()  # a previous app instance (tests, reload) left it in a dead loop
    _task = asyncio.create_task(_run())
    _task_loop = loop


async def stop() -> None:
    global _task, _task_loop
    if _task is None:
        return
    task, _task = _task, None
    task.cancel()
    if _task_loop is not asyncio.get_running_loop():
        _task_loop = None
        return
    try:
        await task
    except asyncio.CancelledError:
        pass
    _task_loop = None
