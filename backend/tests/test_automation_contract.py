"""Contract tests for the real `automation.report` module used by the backend."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automation import report  # noqa: E402
from app.schemas import ReportOut  # noqa: E402

EVENT = {
    "event_id": "evt_stand12_1",
    "type": "RESTRICTED_ZONE",
    "severity": "CRITICAL",
    "camera_id": "stand12",
    "zone_id": "engine-left",
    "detected_at": "2026-10-31T10:42:13Z",
    "duration_s": 1.4,
}


def test_generate_matches_event_out_contract(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    result = report.generate(EVENT)
    parsed = ReportOut.model_validate(result)

    assert parsed.source == "template"
    assert parsed.what == "Persoană în zona restricționată (motor)."
    assert parsed.where == "Camera stand12, zona engine-left."
    assert parsed.when.endswith("timp în zonă 1.4 s.")
    assert parsed.recommended_action == "Oprește activitatea în zonă și contactează persoana prin radio."


def test_generate_handles_camera_offline():
    result = report.generate({**EVENT, "type": "CAMERA_OFFLINE", "severity": "WARNING"})

    assert result["source"] == "template"
    assert "Camera nu mai transmite cadre" in result["what"]
    assert result["where"] == "Camera stand12, zona engine-left."


def test_summarize_uses_backend_shift_shape():
    summary = report.summarize(
        {
            "shift": "morning",
            "date": "2026-10-31",
            "kpi": {"open_incidents": 2, "escalated": 1},
            "by_type": [
                {"type": "RESTRICTED_ZONE", "critical": 1, "warning": 0},
                {"type": "NO_PPE", "critical": 0, "warning": 4},
            ],
        }
    )

    assert "5 evenimente" in summary
    assert "1 critic și" in summary
    assert "4 de avertizare" in summary
    assert "2 rămân deschise" in summary
    assert "1 a fost escaladat" in summary


def test_slack_text_uses_backend_link_and_escalation():
    text = report.slack_text(
        {
            **EVENT,
            "link": "http://localhost:5173/incidents/evt_stand12_1",
            "escalate_after_s": 30,
        },
        escalated=True,
    )

    assert text.startswith("ESCALADARE · neconfirmat de 30 s · [CRITICAL] RESTRICTED_ZONE · stand12 / engine-left · ")
    assert text.endswith(" · http://localhost:5173/incidents/evt_stand12_1")
