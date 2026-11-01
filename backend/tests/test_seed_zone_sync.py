"""The demo edge fixtures may only disagree with the seed about geometry.

A fixture is the per-clip version of a seeded zone: the polygon is drawn on the
clip's first frame and follows the ground, and the name describes what that clip
shows. Everything else — rule type, active condition, required PPE, severity,
debounce, escalation — describes the zone itself and must come from `app.seed`.

The fixtures used to carry their own copy of those fields, and the copy drifted:
`taxiway-b` was declared with another rule than the seed, and `baggage-area`
(a `PPE_REQUIRED` zone) was declared `RESTRICTED` with no required PPE. The edge
then sent an event type the backend did not expect for that zone, and the KPI and
the report counted it under the wrong rule.
"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.models import Zone
from app.seed import seed_cameras, seed_zones

REPO = Path(__file__).resolve().parents[2]
FIXTURES = sorted((REPO / "ml" / "fixtures" / "zones").glob("*.json")) + [
    REPO / "ml" / "fixtures" / "zones.stand12.json"
]

# These may differ per clip. `name` is a description of what that clip shows;
# the polygon is calibrated on the clip's first frame. Everything else changes
# behaviour or what the UI reports, so it must come from the seed.
#
# `camera_id` is deliberately strict: the edge drops every zone whose camera does
# not match the feed, so a wrong camera_id makes the zone silently disappear.
PER_CLIP_FIELDS = {"polygon", "reference_frame", "name"}


class _Session:
    def __init__(self) -> None:
        self.added: list[Zone] = []

    def get(self, _model, _id):
        return None

    def add(self, zone: Zone) -> None:
        self.added.append(zone)


def seeded_zones() -> dict[str, Zone]:
    session = _Session()
    seed_zones(session)
    return {zone.id: zone for zone in session.added}


def test_seed_loads_the_demo_zones():
    # A guard on the guard: if the seed stops loading, the loop below proves nothing.
    assert set(seeded_zones()) >= {"engine-left", "apron-stand12", "taxiway-b", "baggage-area"}


def test_every_fixture_matches_the_seed():
    seeded = seeded_zones()
    problems: list[str] = []

    for path in FIXTURES:
        for zone in json.loads(path.read_text(encoding="utf-8")):
            expected = seeded.get(zone["id"])
            if expected is None:
                problems.append(f"{path.name}: {zone['id']} nu există în seed")
                continue
            for field, value in zone.items():
                if field in PER_CLIP_FIELDS:
                    continue
                seeded_value = getattr(expected, field, None)
                if value != seeded_value:
                    problems.append(f"{path.name}: {zone['id']}.{field} = {value!r}, seed = {seeded_value!r}")
            for field in type(expected).model_fields:
                if field not in PER_CLIP_FIELDS and field not in zone:
                    problems.append(f"{path.name}: {zone['id']} nu are câmpul {field}")

    assert not problems, "\n".join(problems)

def test_camera_fixture_matches_the_seed():
    """The same rule for cameras: the fixture is an export, not a second definition."""
    session = _Session()
    seed_cameras(session)
    seeded = {camera.id: camera for camera in session.added}

    fixture = json.loads((REPO / "backend" / "fixtures" / "cameras.json").read_text(encoding="utf-8"))
    assert {c["id"] for c in fixture} == set(seeded), "fixture și seed au camere diferite"
    for camera in fixture:
        expected = seeded[camera["id"]]
        for field in ("name", "rtsp_url", "online", "engine_on"):
            assert camera[field] == getattr(expected, field), f"{camera['id']}.{field}"


def test_seed_repairs_a_zone_stored_with_a_retired_rule_type(client):
    """A database from before FOD was dropped still holds `taxiway-b` as FOD_WATCH.

    `GET /zones` validates every row, so that one row made the whole list fail with a
    500 and the editor showed no zones at all. The seed takes the rule from the seed
    again, but keeps the polygon the user drew.
    """
    from sqlalchemy import text
    from sqlmodel import Session

    from app.db import get_engine

    drawn = [[0.1, 0.1], [0.5, 0.1], [0.5, 0.5]]
    with Session(get_engine()) as session:
        session.exec(
            text("UPDATE zones SET rule_type = 'FOD_WATCH', required_ppe = '[]', polygon = :polygon WHERE id = 'taxiway-b'"),
            params={"polygon": json.dumps(drawn)},
        )
        session.commit()
    # The bug, before the seed runs again (TestClient re-raises what the server answers with 500).
    with pytest.raises(ValidationError):
        client.get("/zones")

    with Session(get_engine()) as session:
        seed_zones(session)
        session.commit()

    response = client.get("/zones", params={"camera_id": "taxiway-b"})
    assert response.status_code == 200
    (zone,) = response.json()
    seeded = seeded_zones()["taxiway-b"]
    assert zone["rule_type"] == seeded.rule_type
    assert zone["required_ppe"] == seeded.required_ppe
    assert zone["polygon"] == drawn
    assert client.get("/zones").status_code == 200
