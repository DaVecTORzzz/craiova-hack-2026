"""The demo edge fixtures may only disagree with the seed about geometry.

A fixture is the per-clip version of a seeded zone: the polygon is drawn on the
clip's first frame and follows the ground, and the name describes what that clip
shows. Everything else — rule type, active condition, required PPE, severity,
debounce, escalation — describes the zone itself and must come from `app.seed`.

The fixtures used to carry their own copy of those fields, and the copy drifted:
`taxiway-b` (a `FOD_WATCH` zone) was declared `RESTRICTED`, and `baggage-area`
(a `PPE_REQUIRED` zone) was declared `RESTRICTED` with no required PPE. The edge
then sent an event type the backend did not expect for that zone, and the KPI and
the report counted it under the wrong rule.
"""

import json
from pathlib import Path

from app.models import Zone
from app.seed import seed_zones

REPO = Path(__file__).resolve().parents[2]
FIXTURES = sorted((REPO / "ml" / "fixtures" / "zones").glob("*.json")) + [
    REPO / "ml" / "fixtures" / "zones.stand12.json"
]

# These may differ per clip. `name` is a description of what that clip shows;
# the polygon is calibrated on the clip's first frame. Everything else changes
# behaviour or what the UI reports, so it must come from the seed.
PER_CLIP_FIELDS = {"polygon", "reference_frame", "camera_id", "name"}


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


def test_seed_has_four_zones():
    # A guard on the guard: if the seed stops loading, the loop below proves nothing.
    assert sorted(seeded_zones()) == ["apron-stand12", "baggage-area", "engine-left", "taxiway-b"]


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
