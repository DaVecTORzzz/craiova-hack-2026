import io
from PIL import Image
from sqlmodel import Session, select

from app.db import get_engine
from app.models import Snapshot

HEADERS = {"X-Edge-Token": "test-token"}


def create_jpeg_bytes() -> bytes:
    img = Image.new("RGB", (64, 64), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def create_png_bytes() -> bytes:
    img = Image.new("RGB", (64, 64), color=(0, 255, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_upload_jpeg_snapshot_success(client):
    jpeg_bytes = create_jpeg_bytes()
    files = {"file": ("snapshot.jpg", jpeg_bytes, "image/jpeg")}
    event_id = "evt_stand12_1793356933120_17"

    response = client.post(
        "/edge/snapshots",
        files=files,
        data={"event_id": event_id},
        headers=HEADERS,
    )
    assert response.status_code == 201
    data = response.json()
    assert "snapshot_url" in data
    assert data["snapshot_url"] == f"/snapshots/{event_id}.jpg"

    # Returned URL serves the same bytes
    get_res = client.get(data["snapshot_url"])
    assert get_res.status_code == 200
    assert get_res.content == jpeg_bytes

    # Database has snapshot row
    with Session(get_engine()) as session:
        rec = session.exec(select(Snapshot).where(Snapshot.file_name == f"{event_id}.jpg")).first()
        assert rec is not None
        assert rec.expires_at > rec.created_at


def test_upload_jpeg_without_event_id_generates_snap_uuid(client):
    jpeg_bytes = create_jpeg_bytes()
    files = {"file": ("snapshot.jpg", jpeg_bytes, "image/jpeg")}

    response = client.post(
        "/edge/snapshots",
        files=files,
        headers=HEADERS,
    )
    assert response.status_code == 201
    snapshot_url = response.json()["snapshot_url"]
    assert snapshot_url.startswith("/snapshots/snap_")
    assert snapshot_url.endswith(".jpg")

    get_res = client.get(snapshot_url)
    assert get_res.status_code == 200
    assert get_res.content == jpeg_bytes


def test_upload_png_returns_415(client):
    png_bytes = create_png_bytes()
    files = {"file": ("snapshot.png", png_bytes, "image/png")}

    response = client.post(
        "/edge/snapshots",
        files=files,
        headers=HEADERS,
    )
    assert response.status_code == 415
    assert response.json() == {"detail": "only image/jpeg is allowed"}


def test_upload_missing_token_returns_401(client):
    jpeg_bytes = create_jpeg_bytes()
    files = {"file": ("snapshot.jpg", jpeg_bytes, "image/jpeg")}

    # Missing token
    response = client.post("/edge/snapshots", files=files)
    assert response.status_code == 401
    assert response.json() == {"detail": "invalid edge token"}

    # Invalid token
    response_invalid = client.post(
        "/edge/snapshots",
        files=files,
        headers={"X-Edge-Token": "bad-token"},
    )
    assert response_invalid.status_code == 401
    assert response_invalid.json() == {"detail": "invalid edge token"}


def test_upload_file_exceeding_5mb_returns_413(client):
    # Over 5 MB (5 * 1024 * 1024 + 1 bytes)
    large_bytes = b"0" * (5 * 1024 * 1024 + 1)
    files = {"file": ("large.jpg", large_bytes, "image/jpeg")}

    response = client.post(
        "/edge/snapshots",
        files=files,
        headers=HEADERS,
    )
    assert response.status_code == 413
    assert response.json() == {"detail": "file larger than 5 MB"}
