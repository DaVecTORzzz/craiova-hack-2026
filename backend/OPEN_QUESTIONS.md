# Open questions — backend

## For Dalina: `automation/report.py` interface (step 10)

`automation/report.py` does not exist yet. The backend imports it in process (`PYTHONPATH` includes the repo root) and expects:

```python
# automation/report.py  (role D)
def generate(event: dict) -> dict:
    """Returns {what, where, when, severity_reason, recommended_action, source} where source is 'llm' or 'template'."""

def summarize(report: dict) -> str:
    """2-3 sentences from the shift report numbers."""

def slack_text(event: dict, escalated: bool) -> str:   # optional
```

- `generate` runs in a thread with a 3 s budget; on import error, timeout, exception or invalid output the backend uses its own Romanian template (`source="template"`).
- Until the module exists, every report is the backend template and Slack uses the default text.

## Mismatch: `automation/README.md` vs `IMPLEMENTATION_PLAN.md`

`automation/README.md` describes `on_event_created(event)` starting an async task per event, a `Notifier.send(event)` adapter for Slack, and escalation inside `automation/`. The backend plan (7.4–7.6) instead has the backend own Slack sending, escalation timers and `notified_at`, and call only `generate` / `summarize` / `slack_text` from `automation.report`. The backend follows the plan. Max and Dalina need to agree on one split before Dalina writes Slack or escalation code, otherwise notifications would be sent twice.
