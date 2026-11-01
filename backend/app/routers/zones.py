import asyncio
import time
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlmodel import Session, select

from app.config import get_settings
from app.timeutil import utcnow
from app.auth import verify_edge_token
from app.db import get_session
from app.models import Camera, ConfigState, Zone, ZoneProposal
from app.schemas import ZoneIn, ZoneIO, ZoneProposalIO, ZoneProposalsIn

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


def proposal_io(row: ZoneProposal) -> ZoneProposalIO:
    return ZoneProposalIO.model_validate(row.model_dump())


@router.get("/proposals", response_model=list[ZoneProposalIO])
async def list_proposals(
    camera_id: str | None = None,
    session: Session = Depends(get_session),
) -> list[ZoneProposalIO]:
    query = select(ZoneProposal)
    if camera_id is not None:
        query = query.where(ZoneProposal.camera_id == camera_id)
    return [proposal_io(row) for row in session.exec(query.order_by(ZoneProposal.id)).all()]


@router.post("/proposals", response_model=list[ZoneProposalIO], dependencies=[Depends(verify_edge_token)])
async def put_proposals(body: ZoneProposalsIn, session: Session = Depends(get_session)) -> list[ZoneProposalIO]:
    """Replace every proposal of a camera: o analiză nouă înlocuiește una veche."""
    if session.get(Camera, body.camera_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown camera_id")
    for row in session.exec(select(ZoneProposal).where(ZoneProposal.camera_id == body.camera_id)).all():
        session.delete(row)
    created = []
    for proposal in body.proposals:
        row = ZoneProposal(**proposal.model_dump(exclude={"created_at"}), created_at=utcnow())
        session.add(row)
        created.append(row)
    session.commit()
    for row in created:
        session.refresh(row)
    return [proposal_io(row) for row in created]


@router.delete("/proposals/{proposal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_proposal(proposal_id: str, session: Session = Depends(get_session)) -> Response:
    row = session.get(ZoneProposal, proposal_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown proposal_id")
    session.delete(row)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{zone_id}", response_model=ZoneIO)
async def put_zone(
    zone_id: str,
    body: ZoneIn,
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


@router.delete("/{zone_id}/reference-frame", response_model=ZoneIO)
async def delete_reference_frame(
    zone_id: str,
    session: Session = Depends(get_session),
) -> ZoneIO:
    """Drop the reference frame of a zone; the editor falls back to a blank canvas."""
    zone = session.get(Zone, zone_id)
    if zone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown zone_id")
    if zone.reference_frame:
        path = Path(get_settings().snapshot_dir) / "reference" / f"{zone_id}.jpg"
        path.unlink(missing_ok=True)
    zone.reference_frame = None
    session.add(zone)
    bump_config_version(session)
    session.commit()
    session.refresh(zone)
    return zone_io(zone)


@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zone(zone_id: str, session: Session = Depends(get_session)) -> Response:
    zone = session.get(Zone, zone_id)
    if zone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown zone_id")
    session.delete(zone)
    bump_config_version(session)
    session.commit()
    path = Path(get_settings().snapshot_dir) / "reference" / f"{zone_id}.jpg"
    path.unlink(missing_ok=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


LIVE_WAIT_S = 3.0


async def _wait_for_clean_frame(
    live_dir: Path, camera_id: str, since: float, timeout: float = LIVE_WAIT_S
) -> Path | None:
    """Wait for the edge to answer a reference request with a frame without the overlay.

    The watch file is touched meanwhile, because with ``--live-when-watched`` the edge only
    renders the live view while somebody is looking at it.
    """
    clean = live_dir / f"{camera_id}.clean.jpg"
    watch = live_dir / f"{camera_id}.watch"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        watch.touch()
        try:
            if clean.is_file() and clean.stat().st_mtime >= since:
                return clean
        except OSError:
            pass
        await asyncio.sleep(0.1)
    return None


@router.post("/{zone_id}/reference-frame/from-live", response_model=ZoneIO)
async def post_reference_from_live(
    zone_id: str,
    session: Session = Depends(get_session),
) -> ZoneIO:
    """Use the live camera frame (already blurred at the edge) as the zone reference."""
    zone = session.get(Zone, zone_id)
    if zone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown zone_id")

    live_dir = Path(get_settings().snapshot_dir) / "live"
    if not live_dir.is_dir():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="no live frames yet; is the edge running?",
        )

    since = time.time()
    request = live_dir / f"{zone.camera_id}.reference"
    request.touch()
    try:
        clean = await _wait_for_clean_frame(live_dir, zone.camera_id, since)
    finally:
        request.unlink(missing_ok=True)

    if clean is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"the edge for {zone.camera_id} did not send a frame; is the camera live?",
        )

    reference_dir = Path(get_settings().snapshot_dir) / "reference"
    reference_dir.mkdir(parents=True, exist_ok=True)
    (reference_dir / f"{zone_id}.jpg").write_bytes(clean.read_bytes())
    zone.reference_frame = f"/snapshots/reference/{zone_id}.jpg"
    session.add(zone)
    bump_config_version(session)
    session.commit()
    session.refresh(zone)
    return zone_io(zone)
