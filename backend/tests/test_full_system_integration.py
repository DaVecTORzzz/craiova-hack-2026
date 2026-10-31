"""Test de integrare end-to-end pentru întregul sistem SafeSight:
Validează că se leagă ML (adnotări & pipeline), Backend (seed, ingestie, KPI, health, ack)
și modulul de automatizare (rapoarte AI în limba română & sinteză tură).
"""

from sqlmodel import Session
from app.db import get_engine
from app.models import Camera, Zone
from tests.conftest import edge_event
from automation.report import generate, summarize, slack_text

HEADERS = {"X-Edge-Token": "test-token"}


def test_full_system_integration_flow(client):
    # 1. Verificare inițializare & Seed (Camere și Zone calibrate)
    health_res = client.get("/health")
    assert health_res.status_code == 200
    health = health_res.json()
    assert health["status"] in ("ok", "degraded")
    assert health["db"] is True

    cams_res = client.get("/cameras")
    assert cams_res.status_code == 200
    cameras = cams_res.json()
    assert len(cameras) >= 1
    stand12 = next((c for c in cameras if c["id"] == "stand12"), None)
    assert stand12 is not None

    # 2. Control Motor Stand (Comutare PUT /cameras/stand12/engine)
    engine_toggle = client.put("/cameras/stand12/engine", json={"on": True})
    assert engine_toggle.status_code == 200
    assert engine_toggle.json()["engine_on"] is True

    # 3. Ingestie Eveniment Edge (Detecție Zonă Restricționată cu Motor Pornit)
    event_payload = edge_event(
        camera_id="stand12",
        zone_id="engine-left",
        type="RESTRICTED_ZONE",
        severity="CRITICAL",
        context={"engine_on": True}
    )
    ingest_res = client.post("/edge/events", json=event_payload, headers=HEADERS)
    assert ingest_res.status_code == 201
    created_event = ingest_res.json()
    assert created_event["status"] == "open"
    event_id = created_event["event_id"]

    # 4. Actualizare KPI în timp real din backend
    kpi_res = client.get("/kpi")
    assert kpi_res.status_code == 200
    kpi_data = kpi_res.json()
    assert kpi_data["open_incidents"] >= 1
    assert "ppe_compliance" in kpi_data

    # 5. Generare Raport Automat AI (Contract modul D - limba română)
    ai_report = generate(event_payload)
    assert "what" in ai_report
    assert "where" in ai_report
    assert "recommended_action" in ai_report
    assert ai_report["source"] in {"template", "llm"}

    # 6. Salvare raport AI în eveniment
    regen_res = client.post(f"/events/{event_id}/regenerate-report")
    assert regen_res.status_code == 200
    assert regen_res.json()["report"] is not None

    # 7. Confirmare Operator (Acknowledge Human-in-the-Loop)
    ack_res = client.post(
        f"/events/{event_id}/ack",
        json={"operator": "Ariana V."}
    )
    assert ack_res.status_code == 200
    acked_data = ack_res.json()
    assert acked_data["status"] == "acknowledged"
    assert acked_data["acked_by"] == "Ariana V."

    # 8. Generare Raport de Tură & Rezumat Automat
    report_res = client.get("/reports", params={"shift": "morning", "date": "2026-10-31"})
    assert report_res.status_code == 200
    shift_data = report_res.json()
    assert "kpi" in shift_data

    shift_summary = summarize(shift_data)
    assert isinstance(shift_summary, str)
    assert len(shift_summary) > 10

    # 9. Formatare Alertă Notificare Slack
    alert_slack = slack_text({**event_payload, "link": f"http://localhost:5173/incidents/{event_id}"}, escalated=False)
    assert "[CRITICAL] RESTRICTED_ZONE" in alert_slack
    assert event_id in alert_slack
