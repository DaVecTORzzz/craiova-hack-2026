import io
from PIL import Image

HEADERS = {"X-Edge-Token": "test-token"}


def _zone(**overrides) -> dict:
    data = {
        "id": "engine-right",
        "camera_id": "stand12",
        "name": "Motor drept",
        "rule_type": "RESTRICTED",
        "active_when": "engine_on",
        "required_ppe": [],
        "severity": "CRITICAL",
        "debounce_s": 1.0,
        "escalate_after_s": 30,
        "notify_channel": "slack",
        "polygon": [[0.1, 0.1], [0.3, 0.1], [0.3, 0.4], [0.1, 0.4]],
        "reference_frame": None,
    }
    data.update(overrides)
    return data


def _config_version(client, camera_id: str = "stand12") -> int:
    res = client.get("/edge/zones", params={"camera_id": camera_id}, headers=HEADERS)
    assert res.status_code == 200
    return res.json()["config_version"]


def _jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "#3A3A3A").save(buf, format="JPEG")
    return buf.getvalue()


def test_list_cameras_and_zones(client):
    cameras = client.get("/cameras").json()
    assert [c["id"] for c in cameras] == ["baggage-area", "stand12", "taxiway-b"]

    zones = client.get("/zones").json()
    assert [z["id"] for z in zones] == ["apron-stand12", "baggage-area", "engine-left", "taxiway-b"]

    stand12 = client.get("/zones", params={"camera_id": "stand12"}).json()
    assert [z["id"] for z in stand12] == ["apron-stand12", "engine-left"]


def test_b10_put_zone_persists_and_bumps_config_version(client):
    before = _config_version(client)

    res = client.put("/zones/engine-right", json=_zone())
    assert res.status_code == 200
    assert res.json() == _zone()

    edge = client.get("/edge/zones", params={"camera_id": "stand12"}, headers=HEADERS).json()
    assert any(z["id"] == "engine-right" for z in edge["zones"])
    assert edge["config_version"] == before + 1

    # Replace the same zone
    res = client.put("/zones/engine-right", json=_zone(escalate_after_s=None, name="Motor drept 2"))
    assert res.status_code == 200
    stored = [z for z in client.get("/zones").json() if z["id"] == "engine-right"][0]
    assert stored["escalate_after_s"] is None
    assert stored["name"] == "Motor drept 2"
    assert _config_version(client) == before + 2


def test_b11_engine_toggle(client):
    before = _config_version(client)

    res = client.put("/cameras/stand12/engine", json={"on": True})
    assert res.status_code == 200
    assert res.json()["engine_on"] is True

    stand12 = [c for c in client.get("/cameras").json() if c["id"] == "stand12"][0]
    assert stand12["engine_on"] is True

    edge = client.get("/edge/zones", params={"camera_id": "stand12"}, headers=HEADERS).json()
    assert edge["engine_on"] is True
    assert edge["config_version"] == before + 1


def test_engine_unknown_camera_404(client):
    assert client.put("/cameras/nope/engine", json={"on": True}).status_code == 404


def test_put_zone_mismatched_id_422(client):
    assert client.put("/zones/other-id", json=_zone()).status_code == 422


def test_put_zone_two_point_polygon_422(client):
    res = client.put("/zones/engine-right", json=_zone(polygon=[[0.1, 0.1], [0.2, 0.2]]))
    assert res.status_code == 422


def test_put_zone_unknown_camera_404(client):
    assert client.put("/zones/engine-right", json=_zone(camera_id="nope")).status_code == 404


def test_reference_frame_upload(client):
    before = _config_version(client)
    jpeg = _jpeg()

    res = client.post(
        "/zones/reference-frame",
        data={"zone_id": "taxiway-b"},
        files={"file": ("ref.jpg", jpeg, "image/jpeg")},
    )
    assert res.status_code == 200
    assert res.json()["reference_frame"] == "/snapshots/reference/taxiway-b.jpg"
    assert client.get("/snapshots/reference/taxiway-b.jpg").content == jpeg
    assert _config_version(client, "taxiway-b") == before + 1


def test_reference_frame_errors(client):
    jpeg = _jpeg()
    res = client.post(
        "/zones/reference-frame",
        data={"zone_id": "nope"},
        files={"file": ("ref.jpg", jpeg, "image/jpeg")},
    )
    assert res.status_code == 404

    res = client.post(
        "/zones/reference-frame",
        data={"zone_id": "taxiway-b"},
        files={"file": ("ref.png", b"\x89PNG", "image/png")},
    )
    assert res.status_code == 415


def test_edge_zones_requires_token_and_known_camera(client):
    assert client.get("/edge/zones", params={"camera_id": "stand12"}).status_code == 401
    assert client.get("/edge/zones", params={"camera_id": "nope"}, headers=HEADERS).status_code == 404
