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
POLL_INTERVAL_S = 0.01
WATCH_TOUCH_S = 1.0


def current_frame(camera_id: str) -> bytes:
    """Latest live frame for the camera, else the placeholder (OPEN QUESTION Q4)."""
    snapshot_dir = Path(get_settings().snapshot_dir)
    live = snapshot_dir / "live" / f"{camera_id}.jpg"
    path = live if live.exists() else snapshot_dir / "placeholder.jpg"
    return path.read_bytes()


def _live_version(camera_id: str) -> int | None:
    """mtime of the live frame; the edge replaces the file atomically on every write."""
    try:
        return (Path(get_settings().snapshot_dir) / "live" / f"{camera_id}.jpg").stat().st_mtime_ns
    except OSError:
        return None


def _touch_watch(camera_id: str) -> None:
    """Tell the edge someone is viewing this camera: it renders live frames only then
    (`--live-when-watched`). Best effort: the stream never fails because of it."""
    live_dir = Path(get_settings().snapshot_dir) / "live"
    try:
        live_dir.mkdir(parents=True, exist_ok=True)
        (live_dir / f"{camera_id}.watch").touch()
    except OSError:
        pass


async def mjpeg_frames(camera_id: str) -> AsyncIterator[bytes]:
    # The file is checked every POLL_INTERVAL_S and a frame is sent only when it changed,
    # so the browser gets the edge's own rate (up to its --live-fps) instead of a fixed 2 fps.
    # The current frame is resent every FRAME_INTERVAL_S anyway: a placeholder or a
    # stalled edge still shows a picture, and the connection stays alive.
    loop = asyncio.get_running_loop()
    last_version: int | None = None
    last_sent: float | None = None
    last_watch: float | None = None
    while True:
        version = _live_version(camera_id)
        now = loop.time()
        if last_watch is None or now - last_watch >= WATCH_TOUCH_S:
            _touch_watch(camera_id)
            last_watch = now
        if last_sent is None or version != last_version or now - last_sent >= FRAME_INTERVAL_S:
            frame = current_frame(camera_id)
            last_version, last_sent = version, now
            yield b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " + str(len(frame)).encode() + b"\r\n\r\n" + frame + b"\r\n"
        await asyncio.sleep(POLL_INTERVAL_S)


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
