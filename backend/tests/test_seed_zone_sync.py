import json
from pathlib import Path

from app.models import Zone
from app.seed import seed_zones

FIXTURE = Path(__file__).resolve().parents[2] / "ml" / "fixtures" / "zones.stand12.json"


class _Session:
    def __init__(self) -> None:
        self.added: list[Zone] = []

    def get(self, _model, _id):
        return None

    def add(self, zone: Zone) -> None:
        self.added.append(zone)


def test_engine_left_seed_matches_ml_fixture():
    """The UI draws the backend zone; the demo edge uses the ML fixture. They must be the same zone."""
    session = _Session()
    seed_zones(session)
    seeded = next(zone for zone in session.added if zone.id == "engine-left")
    fixture = next(zone for zone in json.loads(FIXTURE.read_text(encoding="utf-8")) if zone["id"] == "engine-left")

    for field in ("camera_id", "name", "rule_type", "active_when", "severity", "debounce_s", "escalate_after_s"):
        assert getattr(seeded, field) == fixture[field], field
    assert [list(point) for point in seeded.polygon] == fixture["polygon"]
