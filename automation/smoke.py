from automation.report import generate, summarize, slack_text

EVENT = {
    "event_id": "evt_demo_1",
    "type": "FOD",
    "severity": "CRITICAL",
    "camera_id": "taxiway-b",
    "zone_id": "taxiway-b",
    "detected_at": "2026-10-31T10:42:13Z",
    "duration_s": 3.0,
}


def main() -> None:
    report = generate(EVENT)
    expected = {"what", "where", "when", "severity_reason", "recommended_action", "source"}
    assert set(report) == expected, f"chei neașteptate: {set(report) ^ expected}"
    assert report["source"] in {"template", "llm"}
    assert "taxiway-b" in report["where"]

    text = slack_text(
        {**EVENT, "link": "http://localhost:5173/incidents/evt_demo_1", "escalate_after_s": 30},
        escalated=True,
    )
    assert text.startswith("ESCALADARE · neconfirmat de 30 s · [CRITICAL] FOD")
    assert text.endswith(" · http://localhost:5173/incidents/evt_demo_1")

    summary = summarize(
        {
            "shift": "morning",
            "date": "2026-10-31",
            "kpi": {"open_incidents": 1, "escalated": 0},
            "by_type": [
                {"type": "FOD", "critical": 1, "warning": 0},
                {"type": "NO_PPE", "critical": 0, "warning": 1},
            ],
        }
    )
    assert "2 evenimente" in summary
    assert "1 critic și 1 de avertizare" in summary

    print("smoke OK:", report["what"])


if __name__ == "__main__":
    main()
