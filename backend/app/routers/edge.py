import re
from datetime import timedelta
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Response, UploadFile, status
from sqlmodel import Session

from app.config import get_settings
from app.db import get_session
from app.models import Snapshot
from app.routers.health import record_edge_seen
from app.schemas import EVENT_ID_PATTERN, EdgeEventIn, EventOut
from app.services.events import ingest
from app.timeutil import utcnow

router = APIRouter(prefix="/edge", tags=["edge"])

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def verify_edge_token(x_edge_token: str | None = Header(default=None, alias="X-Edge-Token")) -> None:
    settings = get_settings()
    if not x_edge_token or x_edge_token != settings.edge_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid edge token",
        )
    record_edge_seen()


@router.post("/events", response_model=EventOut)
async def post_edge_event(
    payload: EdgeEventIn,
    response: Response,
    session: Session = Depends(get_session),
    _token: None = Depends(verify_edge_token),
) -> EventOut:
    out, created = await ingest(session, payload)
    if created:
        response.status_code = status.HTTP_201_CREATED
    else:
        response.status_code = status.HTTP_200_OK
    return out


@router.post("/snapshots", status_code=status.HTTP_201_CREATED)
async def post_edge_snapshot(
    file: UploadFile = File(...),
    event_id: str | None = Form(default=None),
    session: Session = Depends(get_session),
    _token: None = Depends(verify_edge_token),
) -> dict[str, str]:
    if file.content_type != "image/jpeg":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="only image/jpeg is allowed",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="file larger than 5 MB",
        )

    if event_id and re.match(EVENT_ID_PATTERN, event_id):
        file_name = f"{event_id}.jpg"
    else:
        file_name = f"snap_{uuid4().hex}.jpg"

    settings = get_settings()
    snapshot_dir = Path(settings.snapshot_dir)
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    file_path = snapshot_dir / file_name
    file_path.write_bytes(content)

    now = utcnow()
    expires_at = now + timedelta(days=settings.retention_days)
    snapshot_record = Snapshot(
        file_name=file_name,
        path=str(file_path),
        created_at=now,
        expires_at=expires_at,
    )
    session.add(snapshot_record)
    session.commit()

    prefix = settings.snapshot_base_url.rstrip("/")
    snapshot_url = f"{prefix}/snapshots/{file_name}"
    return {"snapshot_url": snapshot_url}
