import time
from fastapi import APIRouter, Response, status
from sqlalchemy import text
from sqlmodel import Session

from app.config import get_settings
from app.db import get_engine
from app.routers.stream import live_rate
from app.services.outbox import notification_stats

router = APIRouter(tags=["health"])

_edge_last_seen: float | None = None


def record_edge_seen(ts: float | None = None) -> None:
    global _edge_last_seen
    _edge_last_seen = ts if ts is not None else time.time()


def get_edge_last_seen_s() -> float | None:
    if _edge_last_seen is None:
        return None
    return time.time() - _edge_last_seen


def check_db() -> bool:
    try:
        with Session(get_engine()) as session:
            session.exec(text("SELECT 1"))
            return True
    except Exception:
        return False


@router.get("/health")
async def health(response: Response):
    settings = get_settings()
    db_ok = check_db()
    edge_last_seen_s = get_edge_last_seen_s()
    mock = settings.use_mock
    # A monitoring endpoint must not fall over harder than the thing it monitors:
    # with the DB down, report null instead of raising.
    notifications = notification_stats() if db_ok else None

    # 7.11: HTTP 200 when db is true (status degraded if edge_last_seen_s is null or > 60 and mock is off), 503 when db is false.
    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "degraded",
            "db": False,
            "edge_last_seen_s": edge_last_seen_s,
            "mock": mock,
            "live_fps": live_rate.snapshot(),
            "notifications": notifications,
        }

    if (edge_last_seen_s is None or edge_last_seen_s > 60) and not mock:
        st = "degraded"
    else:
        st = "ok"

    return {
        "status": st,
        "db": True,
        "edge_last_seen_s": edge_last_seen_s,
        "mock": mock,
        "live_fps": live_rate.snapshot(),
        "notifications": notifications,
    }
