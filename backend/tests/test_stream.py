import asyncio
from pathlib import Path
from app.config import get_settings
from app.routers.stream import mjpeg_frames


def _first_chunk(camera_id: str) -> bytes:
    async def first() -> bytes:
        frames = mjpeg_frames(camera_id)
        try:
            return await anext(frames)
        finally:
            await frames.aclose()

    return asyncio.run(first())


def test_stream_unknown_camera_404(client):
    assert client.get("/stream/nope.mjpg").status_code == 404


def test_stream_serves_placeholder_then_live_frame(client):
    snapshot_dir = Path(get_settings().snapshot_dir)
    placeholder = (snapshot_dir / "placeholder.jpg").read_bytes()

    chunk = _first_chunk("stand12")
    assert chunk.startswith(b"--frame\r\nContent-Type: image/jpeg\r\n")
    assert placeholder in chunk

    (snapshot_dir / "live" / "stand12.jpg").write_bytes(b"\xff\xd8live\xff\xd9")
    assert b"\xff\xd8live\xff\xd9" in _first_chunk("stand12")
