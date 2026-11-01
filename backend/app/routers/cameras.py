import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.db import get_session
from app.models import Camera
from app.routers.zones import bump_config_version
from app.schemas import CameraCreate, CameraOut, EngineIn
from app.timeutil import utcnow

router = APIRouter(prefix="/cameras", tags=["cameras"])


def camera_out(camera: Camera) -> CameraOut:
    return CameraOut(
        id=camera.id,
        name=camera.name,
        rtsp_url=camera.rtsp_url,
        online=camera.online,
        engine_on=camera.engine_on,
    )


@router.get("", response_model=list[CameraOut])
async def list_cameras(session: Session = Depends(get_session)) -> list[CameraOut]:
    cameras = session.exec(select(Camera).order_by(Camera.id)).all()
    return [camera_out(c) for c in cameras]


@router.put("/{camera_id}", response_model=CameraOut)
async def put_camera(
    camera_id: str,
    body: CameraCreate,
    session: Session = Depends(get_session),
) -> CameraOut:
    """Create or rename a camera. The demo uses it for the laptop webcam feed."""
    # Id-ul ajunge în nume de fișiere (live/<id>.jpg, <id>.watch, reference/<id>.jpg),
    # deci trebuie să rămână o cheie simplă.
    if not re.fullmatch(r"[a-z0-9-]{1,64}", camera_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="camera id must match ^[a-z0-9-]+$ (max 64)",
        )
    camera = session.get(Camera, camera_id)
    if camera is None:
        camera = Camera(
            id=camera_id,
            name=body.name,
            rtsp_url=body.rtsp_url or f"demo://{camera_id}",
            engine_on=False,
            online=True,
            updated_at=utcnow(),
        )
    else:
        camera.name = body.name
        if body.rtsp_url:
            camera.rtsp_url = body.rtsp_url
        camera.updated_at = utcnow()
    session.add(camera)
    session.commit()
    session.refresh(camera)
    return camera_out(camera)


@router.put("/{camera_id}/engine", response_model=CameraOut)
async def put_engine(
    camera_id: str,
    body: EngineIn,
    session: Session = Depends(get_session),
) -> CameraOut:
    camera = session.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="unknown camera_id",
        )
    camera.engine_on = body.on
    camera.updated_at = utcnow()
    session.add(camera)
    bump_config_version(session)
    session.commit()
    session.refresh(camera)
    return camera_out(camera)
