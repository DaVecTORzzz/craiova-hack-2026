import sys
import time
import types
import pytest
from tests.conftest import edge_event, wait_for_report

HEADERS = {"X-Edge-Token": "test-token"}

LLM_REPORT = {
    "what": "Persoană lângă motorul stâng.",
    "where": "Stand 12, motor stâng.",
    "when": "10:42:13.",
    "severity_reason": "Motor pornit.",
    "recommended_action": "Oprește activitatea în zonă.",
    "source": "llm",
}


def _fake_automation(monkeypatch: pytest.MonkeyPatch, generate) -> None:
    package = types.ModuleType("automation")
    module = types.ModuleType("automation.report")
    module.generate = generate
    package.report = module
    monkeypatch.setitem(sys.modules, "automation", package)
    monkeypatch.setitem(sys.modules, "automation.report", module)


def _create_event(client, **overrides) -> str:
    payload = edge_event(**overrides)
    assert client.post("/edge/events", json=payload, headers=HEADERS).status_code == 201
    return payload["event_id"]


def test_template_report_without_automation(client, monkeypatch):
    monkeypatch.setitem(sys.modules, "automation", None)
    ev_id = _create_event(client, duration_s=1.4)

    report = wait_for_report(client, ev_id)["report"]
    assert report["source"] == "template"
    assert report["what"] == "Persoană în zona engine-left."
    assert report["where"] == "Camera stand12, zona engine-left."
    assert report["when"].endswith(", timp în zonă 1.4 s.")
    assert report["severity_reason"] == "Zonă restricționată activă; risc de accident."
    assert report["recommended_action"] == "Oprește activitatea în zonă și contactează persoana prin radio."


def test_template_report_camera_offline(client, monkeypatch):
    monkeypatch.setitem(sys.modules, "automation", None)
    ev_id = _create_event(client, type="CAMERA_OFFLINE", severity="WARNING")

    report = wait_for_report(client, ev_id)["report"]
    assert report["what"] == "Camera stand12 nu mai transmite cadre."
    assert report["recommended_action"] == "Verifică alimentarea și rețeaua camerei."


def test_slow_automation_falls_back_after_3s(client, monkeypatch):
    def slow_generate(event: dict) -> dict:
        time.sleep(5)
        return LLM_REPORT

    _fake_automation(monkeypatch, slow_generate)
    ev_id = _create_event(client)

    start = time.monotonic()
    res = client.post(f"/events/{ev_id}/regenerate-report")
    elapsed = time.monotonic() - start

    assert res.status_code == 200
    assert res.json()["report"]["source"] == "template"
    assert 2.5 < elapsed < 4.5


def test_automation_report_is_used(client, monkeypatch):
    received: list[dict] = []

    def generate(event: dict) -> dict:
        received.append(event)
        return LLM_REPORT

    _fake_automation(monkeypatch, generate)
    ev_id = _create_event(client)

    report = wait_for_report(client, ev_id)["report"]
    assert report == LLM_REPORT
    assert received[0]["event_id"] == ev_id


def test_invalid_automation_output_falls_back(client, monkeypatch):
    _fake_automation(monkeypatch, lambda event: {"what": "incomplet"})
    ev_id = _create_event(client)

    assert wait_for_report(client, ev_id)["report"]["source"] == "template"


def test_regenerate_report_replaces_existing(client, monkeypatch):
    monkeypatch.setitem(sys.modules, "automation", None)
    ev_id = _create_event(client)
    assert wait_for_report(client, ev_id)["report"]["source"] == "template"

    _fake_automation(monkeypatch, lambda event: LLM_REPORT)
    res = client.post(f"/events/{ev_id}/regenerate-report")
    assert res.status_code == 200
    assert res.json()["report"] == LLM_REPORT


def test_regenerate_report_unknown_event_404(client):
    assert client.post("/events/evt_stand12_0000000000000_1/regenerate-report").status_code == 404
