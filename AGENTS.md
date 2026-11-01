# SafeSight — Agent Guide

SafeSight transforms existing airport-apron cameras into structured safety events: edge detection → event → operator alert → AI incident report. The demo path below is the core flow and must keep working.

This file is the single source of truth for agents. `CLAUDE.md` only forwards here. Read it before touching code and update it in the same change when a durable rule changes.

## Session start

Run `./scripts/agent-preflight.sh` before any task. It fetches both repos and pulls `main` only when the working tree is clean. If it fails, stop and report; do not work on stale repos. This is tool-agnostic: Claude, Codex, opencode, Cursor and any other agent read `AGENTS.md`; the script does not depend on a specific harness.

## Read first

- `docs/contract.md` — canonical event, zone and endpoint contract. Do not invent fields.
- `README.md` — module map and owners.
- The README of the folder you touch — exact commands and verification.
- Internal role briefs A–D — private repo `DaVecTORzzz/safesight-docs` (Typst + PDF). They explain; `docs/contract.md` wins.

## Stack

Python 3.12 + `uv`, FastAPI, Pydantic v2, SQLite/SQLModel, YOLO26 (`YOLO26s`/`YOLO26n`; `YOLO11s` only as benchmark fallback), React 19 + Vite + TypeScript, Slack incoming webhook.

## Contract hot points

- Edge sends detection fields only. `status`, `report`, `received_at`, `notified_at`, `escalated_at`, `acked_at`, `acked_by` belong to backend.
- `snapshot_url` is an HTTP URL served by the API; never `minio://`.
- `confidence` is `{ detector, temporal: { seen, window } }`, not a string.
- Severity is only `CRITICAL` or `WARNING`; `RESOLVED` is a status. No `verifying`.
- Slack: text + link, no images, no buttons.
- FOD: 3 s in demo, 10 s in production. Smoke is stretch and not in the demo.
- Details and examples: `docs/contract.md`.
- `docs/contract.md` changes only via a separate PR approved by all consumers.

## Commands

Use the exact command from the module README when it exists. Target commands:

- API health: `curl localhost:8000/health`
- ML smoke: `python -m ml.smoke <video.mp4>`
- Automation smoke: `python -m automation.smoke`
- Frontend build: `npm run build`
- Full stack: `docker compose up` (when the compose file exists)

Before finishing: run the check for the affected module and re-run the demo path. If you cannot run it, say which command failed and why.

## Demo path

1. Person enters the engine zone → `RESTRICTED_ZONE` appears in Live.
2. Incident detail shows snapshot, timeline and report.
3. Slack receives text + link.
4. Operator acks; escalation stops.
5. Shift report shows KPI + summary.

## Delivery

- Every external dependency has a fallback: recorded demo, template report, mock events.
- Say what is real, what is stock and what is simulated.
- Any agent may change any folder; module owners in `README.md` are contacts, not gatekeepers.

## Working rules

- Read the affected files before editing. Implement only the requested scope.
- Reuse existing patterns; do not add abstractions without a second use.
- Do not weaken or delete a check to make something pass. Fix it or report it.
- Alerts never go straight to Slack. `ingest()` writes the event and its `notification_outbox` row in one transaction; escalation uses the same path (`kind="escalation"`); an ack cancels what is still queued. The worker retries, and `notify.deliver()` sets `notified_at` only on a real success. A `failed` row stays in the table on purpose.

## Boundaries

- Ask before: new dependency, contract change, deleting files, git push/merge, full build.
- Never: force push, `reset --hard`, commit secrets.
- No unblurred faces, no names, no emotion recognition. Blur at the edge before saving or uploading.
- No `.env`, models (`.pt`, `.onnx`), videos (`.mp4`) or local DBs in git.
- `main` stays runnable. Small diffs. No broad refactors or speculative abstractions.
- Commit/push/merge only when the human explicitly asks.

## When stuck

Read the contract and affected files; propose a 3-line plan; ask one clarifying question; do not guess. If you find an inconsistency, stop and report it instead of working around it.

## Progressive disclosure

`docs/contract.md` · `demo/run_sheet.md` · `data/videos/README.md` · `data/annotations/README.md` · module READMEs.
