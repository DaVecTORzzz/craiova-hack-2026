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


def test_stream_sends_a_new_live_frame_without_waiting_half_a_second(client):
    import time

    from app.routers.stream import FRAME_INTERVAL_S

    live = Path(get_settings().snapshot_dir) / "live" / "stand12.jpg"
    live.write_bytes(b"\xff\xd8one\xff\xd9")

    async def two_frames() -> tuple[bytes, bytes, float]:
        frames = mjpeg_frames("stand12")
        try:
            first = await anext(frames)
            live.write_bytes(b"\xff\xd8two\xff\xd9")
            started = time.monotonic()
            second = await anext(frames)
            return first, second, time.monotonic() - started
        finally:
            await frames.aclose()

    first, second, waited = asyncio.run(two_frames())
    assert b"one" in first
    assert b"two" in second
    assert waited < FRAME_INTERVAL_S / 2
