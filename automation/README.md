# automation/ — raport AI, rezumat de tură, text Slack

Responsabil: **Dalina**

Backend-ul deține ingestia, escaladarea și trimiterea efectivă către Slack. Acest modul expune doar textele; nu trimite notificări și nu ține timere, ca să nu apară duplicate.

## Interfața așteptată de backend

```python
# automation/report.py
def generate(event: dict) -> dict:
    """Returnează {what, where, when, severity_reason, recommended_action, source}."""

def summarize(report: dict) -> str:
    """2–3 propoziții din cifrele raportului de tură."""

def slack_text(event: dict, escalated: bool) -> str:  # opțional
    """Textul pentru Slack; dacă lipsește, backend-ul folosește șablonul lui."""
```

- `generate` primește un `EventOut` de la backend: `type` uppercase (`RESTRICTED_ZONE`, `NO_PPE`, `FOD`, `SMOKING`, `CAMERA_OFFLINE`), `camera_id`, `zone_id`, `detected_at`, `duration_s`. Întoarce exact cele șase chei, iar `source` este doar `template` sau `llm`; altfel backend-ul respinge raportul și folosește șablonul lui.
- `summarize` primește raportul de tură al backend-ului: `shift`, `date`, `kpi` (`open_incidents`, `escalated`) și `by_type` ca listă de `{type, critical, warning}`. Totalul se calculează din listă.
- `slack_text` primește și `link` (construit de backend din `APP_BASE_URL`) și, la escaladare, `escalate_after_s`; fără ele textul ar avea un URL greșit sau ar pierde linkul.
- `generate` rulează în thread cu buget de 3 s; dacă lipsește, pică sau întoarce invalid, backend-ul folosește șablonul românesc cu `source="template"`.
- Acțiunea recomandată vine din tabelul fix pe tip; LLM-ul doar reformulează.
- Model: Groq `openai/gpt-oss-20b` (configurabil prin `GROQ_MODEL`), mod JSON, temperatură 0,2. `qwen/qwen3.8-27b` rămâne candidat de test (preview).
- Textul Slack: severitate, tip, cameră/zonă, oră locală și link; fără imagini și fără butoane.
- Escaladarea și `notified_at` sunt ale backend-ului. Modulul D nu apelează webhook-ul.

## Verificare

```bash
python -m automation.smoke
python -m automation.report
cd backend && PYTHONPATH=.. uv run pytest -q
```

`smoke` verifică exact contractul backend-ului (chei, `source`, link, escaladare, rezumat), `report` arată un exemplu complet, iar testele backend rulează și modulul real, nu doar fallback-ul.
