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

## Stability run (step 16)

Setup: local `uvicorn` (no Docker), `USE_MOCK=true`, `MOCK_INTERVAL_S=1`, Slack simulated, no `automation/` module. There is no frontend app yet, so one Python WebSocket client on `/ws/events` stood in for the browser tab. Every 60 s: process RSS and 5 × `GET /events?limit=500`.

**Run 1 — 60 min (~3,600 events), before the fix in `18f60c5`:**
- Memory stable: 78 MB at start, 73–76 MB for the rest of the hour.
- WebSocket: one connection the whole hour, no errors; ~3,600 `event.created`, ~7,150 `event.updated`.
- No errors in the API log.
- `GET /events?limit=500`: ~300 ms p50, up to 386 ms max. **Over the 200 ms target.** Cause: one `report_texts` query per event. Fixed in `18f60c5` (one prefetch query, kept referenced).

**Run 2 — 10 min (~600 events), after the fix:**
- Memory 78 → 88 MB while the table fills up to the first 500 events; run 1 showed no growth after that.
- WebSocket: one connection, no errors. No errors in the API log.
- `GET /events?limit=500` at 500 events: ~100 ms p50, 210–224 ms max (single outliers while mock events are written).

Result: p50 is under 200 ms; the max still goes slightly over 200 ms under load. Not optimized further. Decision for Max: accept it, or ask Ariana to request `limit=100` (the API default) in Live.
