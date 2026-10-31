import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from app.config import get_settings
from app.db import get_session
from app.models import Camera

router = APIRouter(tags=["stream"])

FRAME_INTERVAL_S = 0.5


def current_frame(camera_id: str) -> bytes:
    """Latest live frame for the camera, else the placeholder (OPEN QUESTION Q4)."""
    snapshot_dir = Path(get_settings().snapshot_dir)
    live = snapshot_dir / "live" / f"{camera_id}.jpg"
    path = live if live.exists() else snapshot_dir / "placeholder.jpg"
    return path.read_bytes()


async def mjpeg_frames(camera_id: str) -> AsyncIterator[bytes]:
    while True:
        frame = current_frame(camera_id)
        yield b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " + str(len(frame)).encode() + b"\r\n\r\n" + frame + b"\r\n"
        await asyncio.sleep(FRAME_INTERVAL_S)


@router.get("/stream/{camera_id}.mjpg")
async def stream_camera(
    camera_id: str,
    session: Session = Depends(get_session),
) -> StreamingResponse:
    if session.get(Camera, camera_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="unknown camera_id",
        )
    return StreamingResponse(mjpeg_frames(camera_id), media_type="multipart/x-mixed-replace; boundary=frame")
