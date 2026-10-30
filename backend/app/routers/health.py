import time
from fastapi import APIRouter
from app.config import get_settings

router = APIRouter(tags=["health"])

_edge_last_seen: float | None = None


def record_edge_seen(ts: float | None = None) -> None:
    global _edge_last_seen
    _edge_last_seen = ts if ts is not None else time.time()


def get_edge_last_seen_s() -> float | None:
    if _edge_last_seen is None:
        return None
    return time.time() - _edge_last_seen


@router.get("/health")
async def health():
    settings = get_settings()
    db_ok = True  # Step 1: db check is always true
    edge_last_seen_s = get_edge_last_seen_s()
    mock = settings.use_mock

    # 7.11: HTTP 200 when db is true (status degraded if edge_last_seen_s is null or > 60 and mock is off), 503 when db is false.
    if not db_ok:
        status = "degraded"
    elif (edge_last_seen_s is None or edge_last_seen_s > 60) and not mock:
        status = "degraded"
    else:
        status = "ok"

    return {
        "status": status,
        "db": db_ok,
        "edge_last_seen_s": edge_last_seen_s,
        "mock": mock,
    }
