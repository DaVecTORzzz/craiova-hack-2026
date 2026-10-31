from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.db import get_session
from app.models import Camera
from app.routers.zones import bump_config_version
from app.schemas import CameraOut, EngineIn
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
