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

- `generate` rulează în thread cu buget de 3 s; dacă lipsește, pică sau întoarce invalid, backend-ul folosește șablonul românesc cu `source="template"`.
- Acțiunea recomandată vine din tabelul fix pe tip; LLM-ul doar reformulează.
- Model: Groq `openai/gpt-oss-20b` (configurabil prin `GROQ_MODEL`), mod JSON, temperatură 0,2. `qwen/qwen3.8-27b` rămâne candidat de test (preview).
- Textul Slack: severitate, tip, cameră/zonă, oră locală și link; fără imagini și fără butoane.
- Escaladarea și `notified_at` sunt ale backend-ului. Modulul D nu apelează webhook-ul.

## Verificare

```bash
python -m automation.smoke
python -m automation.report
```

Prima comandă verifică un text de raport; a doua generează un raport dintr-un fixture. Backend-ul are propriile teste pentru fallback și timeout.
