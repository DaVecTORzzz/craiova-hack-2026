"""Outbox durabil pentru notificări.

`ingest()` nu mai trimite direct către Slack: scrie un rând în
`notification_outbox`, iar worker-ul îl trimite cu retry. Textul e randat la
enqueue, deci un retry după 30 s trimite exact mesajul original, cu ora
originală, nu ora retrimiterii.

Ce garantează: alerta nu se pierde la un timeout, un 429 sau un restart al
backend-ului; fiecare încercare e consemnată.
Ce nu garantează: că Slack acceptă mesajul. Dacă Slack e jos două minute,
alerta pleacă la revenire; dacă nu pleacă deloc, rândul rămâne `failed`.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.config import get_settings
from app.db import get_engine
from app.models import NotificationOutbox
from app.services import notify
from app.timeutil import utcnow

logger = logging.getLogger("safesight.outbox")

NO_WEBHOOK = "no webhook configured"

_worker: asyncio.Task | None = None
_worker_loop: asyncio.AbstractEventLoop | None = None
# Created lazily per event loop: a module-level Event binds to the first loop it
# touches, and a second app (tests, reload) would fail with "bound to a different loop".
_wake: asyncio.Event | None = None
_wake_loop: asyncio.AbstractEventLoop | None = None


def _waiter() -> asyncio.Event:
    global _wake, _wake_loop
    loop = asyncio.get_running_loop()
    if _wake is None or _wake_loop is not loop:
        _wake = asyncio.Event()
        _wake_loop = loop
    return _wake


def _wakeup() -> None:
    try:
        waiter = _waiter()
    except RuntimeError:  # no running loop: the periodic tick will pick the row up
        return
    waiter.set()


def enqueue(event_id: str, kind: str, text: str, session: Session | None = None) -> bool:
    """Store one notification to send. Idempotent per ``(event_id, kind)``.

    With ``session``, the row joins the caller's transaction: it is committed
    exactly when the caller commits (the event and its alert are atomic). Without
    it, the row is committed here.
    """
    now = utcnow()
    owns_session = session is None
    db = Session(get_engine()) if owns_session else session
    try:
        existing = db.exec(
            select(NotificationOutbox)
            .where(NotificationOutbox.event_id == event_id)
            .where(NotificationOutbox.kind == kind)
        ).first()
        if existing is not None:
            return False
        db.add(
            NotificationOutbox(
                event_id=event_id,
                kind=kind,
                text=text,
                status="pending",
                attempts=0,
                next_attempt_at=now,
                created_at=now,
            )
        )
        if owns_session:
            db.commit()
        else:
            db.flush()
    except IntegrityError:
        # Two enqueues raced: the unique constraint keeps one row, which is the point.
        if owns_session:
            db.rollback()
            return False
        raise
    finally:
        if owns_session:
            db.close()
    _wakeup()
    return True


def _backoff_s(attempts: int) -> float:
    raw = get_settings().outbox_backoff_s
    try:
        steps = [float(part) for part in raw.split(",") if part.strip()]
    except ValueError:
        steps = []
    if not steps:
        steps = [1.0]
    return steps[min(max(attempts, 1) - 1, len(steps) - 1)]


def cancel_pending(event_id: str, prefix: str = "") -> int:
    """Mark the event's queued notifications as cancelled. Returns how many.

    Used when the operator acts first: an escalation that has not left yet must
    not arrive after the acknowledgement that made it pointless.
    """
    with Session(get_engine()) as session:
        rows = session.exec(
            select(NotificationOutbox)
            .where(NotificationOutbox.event_id == event_id)
            .where(NotificationOutbox.status == "pending")
        ).all()
        cancelled = 0
        for row in rows:
            if not row.kind.startswith(prefix):
                continue
            row.status = "cancelled"
            session.add(row)
            cancelled += 1
        if cancelled:
            session.commit()
    return cancelled


async def _deliver(kind: str, event_id: str, text: str) -> tuple[bool, str | None]:
    if kind == "new":
        return await notify.deliver(event_id, text)
    if await notify.send_slack(text):
        return True, None
    return False, "send failed"


def _record(row_id: int, ok: bool, error: str | None) -> None:
    settings = get_settings()
    now = utcnow()
    with Session(get_engine()) as session:
        row = session.get(NotificationOutbox, row_id)
        if row is None or row.status != "pending":
            return
        row.attempts += 1
        if ok:
            row.status = "sent"
            row.sent_at = now
            row.last_error = None
        elif not settings.slack_webhook_url:
            # Nothing to retry against: one honest `failed` row, not an endless log loop.
            row.status = "failed"
            row.last_error = NO_WEBHOOK
        else:
            row.last_error = error or "send failed"
            if row.attempts >= settings.outbox_max_attempts:
                row.status = "failed"
            else:
                row.next_attempt_at = now + timedelta(seconds=_backoff_s(row.attempts))
        session.add(row)
        session.commit()


async def drain_once(limit: int = 20) -> int:
    """Send every due row once. Returns how many rows were attempted."""
    now = utcnow()
    with Session(get_engine()) as session:
        rows = session.exec(
            select(NotificationOutbox)
            .where(NotificationOutbox.status == "pending")
            .where(NotificationOutbox.next_attempt_at <= now)
            .order_by(NotificationOutbox.next_attempt_at)
            .limit(limit)
        ).all()
        due = [(row.id, row.event_id, row.kind, row.text) for row in rows]

    sent = 0
    for row_id, event_id, kind, text in due:
        try:
            ok, error = await _deliver(kind, event_id, text)
        except Exception as exc:  # noqa: BLE001 - one bad notification must not kill the worker
            ok, error = False, type(exc).__name__
        if ok:
            sent += 1
        _record(row_id, ok, error)
    if due:
        logger.info(f"outbox drain attempted={len(due)} sent={sent}")
    return len(due)


def notification_stats() -> dict[str, int | float | None]:
    """State of the outbox for /health: what is stuck and for how long.

    Counts, not hydrated rows: the table grows by one row per event and /health
    is polled every few seconds.
    """
    now = utcnow()
    day_ago = now - timedelta(hours=24)
    with Session(get_engine()) as session:
        pending = session.exec(
            select(func.count())
            .select_from(NotificationOutbox)
            .where(NotificationOutbox.status == "pending")
        ).one()
        failed = session.exec(
            select(func.count())
            .select_from(NotificationOutbox)
            .where(NotificationOutbox.status == "failed")
            .where(NotificationOutbox.created_at >= day_ago)
        ).one()
        oldest = session.exec(
            select(func.min(NotificationOutbox.created_at)).where(NotificationOutbox.status == "pending")
        ).one()
    return {
        "pending": int(pending or 0),
        "failed_24h": int(failed or 0),
        "oldest_pending_s": round((now - oldest).total_seconds(), 1) if oldest is not None else None,
    }


async def _run() -> None:
    interval = get_settings().outbox_interval_s
    while True:
        try:
            await asyncio.wait_for(_waiter().wait(), timeout=interval)
        except TimeoutError:
            pass
        _waiter().clear()
        try:
            await drain_once()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - the worker outlives a bad drain
            logger.warning(f"outbox drain failed: {type(exc).__name__}")


def start() -> None:
    global _worker, _worker_loop
    loop = asyncio.get_running_loop()
    if _worker is not None and not _worker.done() and _worker_loop is loop:
        return
    if _worker is not None and _worker_loop is not loop:
        # A previous app instance (tests, reload) left its worker in a loop that is gone.
        _worker.cancel()
    _worker = asyncio.create_task(_run())
    _worker_loop = loop


async def stop() -> None:
    global _worker, _worker_loop
    if _worker is None:
        return
    worker, _worker = _worker, None
    worker.cancel()
    if _worker_loop is not asyncio.get_running_loop():
        # Awaiting a task from another (closed) loop would raise; cancelling is enough.
        _worker_loop = None
        return
    try:
        await worker
    except asyncio.CancelledError:
        pass
    _worker_loop = None
