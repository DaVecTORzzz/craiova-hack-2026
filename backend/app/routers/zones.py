from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlmodel import Session, select

from app.config import get_settings
from app.db import get_session
from app.models import Camera, ConfigState, Zone
from app.schemas import ZoneIO

router = APIRouter(prefix="/zones", tags=["zones"])

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def zone_io(zone: Zone) -> ZoneIO:
    return ZoneIO.model_validate(zone.model_dump())


def bump_config_version(session: Session) -> int:
    """Increment config_version (7.7). The caller commits."""
    state = session.get(ConfigState, 1)
    if state is None:
        state = ConfigState(id=1, config_version=1)
    state.config_version += 1
    session.add(state)
    return state.config_version


def get_config_version(session: Session) -> int:
    state = session.get(ConfigState, 1)
    return state.config_version if state is not None else 1


@router.get("", response_model=list[ZoneIO])
async def list_zones(
    camera_id: str | None = None,
    session: Session = Depends(get_session),
) -> list[ZoneIO]:
    query = select(Zone)
    if camera_id is not None:
        query = query.where(Zone.camera_id == camera_id)
    zones = session.exec(query.order_by(Zone.id)).all()
    return [zone_io(z) for z in zones]


@router.put("/{zone_id}", response_model=ZoneIO)
async def put_zone(
    zone_id: str,
    body: ZoneIO,
    session: Session = Depends(get_session),
) -> ZoneIO:
    if body.id != zone_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="zone id in body does not match the URL",
        )
    if session.get(Camera, body.camera_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="unknown camera_id",
        )

    data = body.model_dump(mode="json")
    zone = session.get(Zone, zone_id)
    if zone is None:
        zone = Zone(**data)
    else:
        for field, value in data.items():
            setattr(zone, field, value)
    session.add(zone)
    bump_config_version(session)
    session.commit()
    session.refresh(zone)
    return zone_io(zone)


@router.post("/reference-frame", response_model=ZoneIO)
async def post_reference_frame(
    zone_id: str = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> ZoneIO:
    zone = session.get(Zone, zone_id)
    if zone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="unknown zone_id",
        )
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

    reference_dir = Path(get_settings().snapshot_dir) / "reference"
    reference_dir.mkdir(parents=True, exist_ok=True)
    (reference_dir / f"{zone_id}.jpg").write_bytes(content)

    zone.reference_frame = f"/snapshots/reference/{zone_id}.jpg"
    session.add(zone)
    bump_config_version(session)
    session.commit()
    session.refresh(zone)
    return zone_io(zone)
