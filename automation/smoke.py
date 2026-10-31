from automation.report import generate, summarize, slack_text


def main() -> None:
    report = generate({"type": "fod", "camera": "cam01", "zone": "taxiway A"})
    expected = {"what", "where", "when", "severity_reason", "recommended_action", "source"}
    assert expected <= set(report), f"lipsesc chei din raport: {expected - set(report)}"
    assert report["source"] in {"rules-fallback", "llm"}

    text = slack_text({"type": "no_ppe", "camera": "cam02"}, escalated=True)
    assert "MEDIE" in text and "cam02" in text and "ESCALADAT" in text

    summary = summarize({"total": 2, "by_severity": {"ridicata": 1, "medie": 1},
                         "by_type": {"fod": 2}, "escalated": 0})
    assert "2 evenimente" in summary

    print("smoke OK:", report["what"])


if __name__ == "__main__":
    main()
