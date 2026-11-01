import io
from PIL import Image
from sqlmodel import Session

from app.db import get_engine
from app.models import Zone

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


def test_put_zone_self_crossing_polygon_422(client):
    # Points clicked out of order: an hourglass instead of a perimeter.
    hourglass = [[0.1, 0.1], [0.3, 0.1], [0.1, 0.4], [0.3, 0.4]]
    res = client.put("/zones/engine-right", json=_zone(polygon=hourglass))
    assert res.status_code == 422
    assert "cross" in res.text
    assert client.get("/zones", params={"camera_id": "stand12"}).json()  # nothing broke


def test_put_zone_concave_polygon_is_accepted(client):
    arrow = [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.5, 0.4], [0.1, 0.9]]
    res = client.put("/zones/engine-right", json=_zone(polygon=arrow))
    assert res.status_code == 200
    assert res.json()["polygon"] == arrow


def test_stored_crossing_zone_is_still_listed(client):
    """The check is on PUT only: a crossing zone stored earlier must not break GET /zones."""
    from sqlmodel import Session

    from app.db import get_engine
    from app.models import Zone

    with Session(get_engine()) as session:
        zone = session.get(Zone, "engine-left")
        zone.polygon = [[0.1, 0.1], [0.3, 0.1], [0.1, 0.4], [0.3, 0.4]]
        session.add(zone)
        session.commit()
    res = client.get("/zones", params={"camera_id": "stand12"})
    assert res.status_code == 200
    assert any(z["id"] == "engine-left" for z in res.json())
    assert client.get("/edge/zones", params={"camera_id": "stand12"}, headers=HEADERS).status_code == 200


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


def test_delete_zone_removes_it_and_bumps_config_version(client):
    before = _config_version(client)
    assert client.put("/zones/engine-right", json=_zone()).status_code == 200

    res = client.delete("/zones/engine-right")
    assert res.status_code == 204
    assert all(z["id"] != "engine-right" for z in client.get("/zones").json())
    assert _config_version(client) == before + 2

    assert client.delete("/zones/engine-right").status_code == 404


def test_delete_reference_frame_clears_the_field_and_the_file(client):
    jpeg = b"\xff\xd8\xff\xd9"
    client.post(
        "/zones/reference-frame",
        data={"zone_id": "taxiway-b"},
        files={"file": ("ref.jpg", jpeg, "image/jpeg")},
    )

    res = client.delete("/zones/taxiway-b/reference-frame")
    assert res.status_code == 200
    assert res.json()["reference_frame"] is None
    assert client.get("/snapshots/reference/taxiway-b.jpg").status_code == 404

    assert client.delete("/zones/nope/reference-frame").status_code == 404


def test_reference_frame_from_live_copies_the_edge_frame(client, tmp_path, monkeypatch):
    from app.routers import zones as zones_router

    clean = tmp_path / "taxiway-b.clean.jpg"
    clean.write_bytes(b"\xff\xd8\xff\xd9")

    async def fake_wait(live_dir, camera_id, since, timeout=0):
        return clean

    monkeypatch.setattr(zones_router, "_wait_for_clean_frame", fake_wait)

    res = client.post("/zones/taxiway-b/reference-frame/from-live")
    assert res.status_code == 200
    assert res.json()["reference_frame"] == "/snapshots/reference/taxiway-b.jpg"
    assert client.get("/snapshots/reference/taxiway-b.jpg").content == b"\xff\xd8\xff\xd9"


def test_reference_frame_from_live_reports_a_silent_edge(client, monkeypatch):
    from app.routers import zones as zones_router

    async def no_frame(live_dir, camera_id, since, timeout=0):
        return None

    monkeypatch.setattr(zones_router, "_wait_for_clean_frame", no_frame)
    res = client.post("/zones/taxiway-b/reference-frame/from-live")
    assert res.status_code == 409
    assert "did not send a frame" in res.json()["detail"]

    assert client.post("/zones/nope/reference-frame/from-live").status_code == 404


def _store_legacy_zone(zone_id: str = "legacy-fod", rule_type: str = "FOD_WATCH") -> None:
    """A row as an older database really holds it: the rule no longer exists in the contract."""
    with Session(get_engine()) as session:
        session.add(
            Zone(
                id=zone_id,
                camera_id="stand12",
                name="Zonă veche",
                rule_type=rule_type,
                active_when="always",
                required_ppe=[],
                severity="WARNING",
                debounce_s=3.0,
                notify_channel="slack",
                escalate_after_s=None,
                polygon=[[0.1, 0.1], [0.3, 0.1], [0.3, 0.4]],
                reference_frame=None,
            )
        )
        session.commit()


def test_a_zone_with_a_retired_rule_is_skipped_not_fatal(client, caplog):
    """The seed repairs the ids it knows; a user-created zone can still hold a retired rule."""
    _store_legacy_zone()

    with caplog.at_level("WARNING", logger="safesight.zones"):
        response = client.get("/zones")

    assert response.status_code == 200
    ids = {zone["id"] for zone in response.json()}
    assert "legacy-fod" not in ids
    assert {"engine-left", "apron-stand12", "taxiway-b", "baggage-area"} <= ids
    assert "legacy-fod" in caplog.text
    assert "FOD_WATCH" in caplog.text


def test_the_edge_config_poll_survives_a_retired_zone(client):
    """One bad row must not stop an edge from receiving the zones it can enforce."""
    _store_legacy_zone()

    response = client.get("/edge/zones", params={"camera_id": "stand12"}, headers=HEADERS)

    assert response.status_code == 200
    ids = {zone["id"] for zone in response.json()["zones"]}
    assert "legacy-fod" not in ids
    assert {"engine-left", "apron-stand12"} <= ids
