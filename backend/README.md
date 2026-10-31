# backend/ — API, rule engine, stream, stocare

Responsabil: **Max**

Brief intern: `safesight-docs/02_B_backend.typ` (repo privat).

- FastAPI + Uvicorn, Pydantic v2, SQLite prin SQLModel. Postgres doar plan B, cu aceeași schemă.
- Ingestie edge: `POST /edge/events` idempotent după `event_id`; `POST /edge/snapshots`; `GET /edge/zones` cu `X-Edge-Token`.
- Rule engine: debounce per `(track_id, zone_id, type)`, un singur eveniment per track, cooldown, context `engine_on`, severitate.
- Stream MJPEG pe `/stream/{camera_id}.mjpg`, WebSocket pe `/ws/events` doar cu `event.created` și `event.updated`.
- Acțiuni operator: ack, fals pozitiv, reopen; fiecare intră în `event_actions` cu operator și momentul acțiunii.
- Planul de implementare pas cu pas: [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md).
- Escaladare per zonă (`escalate_after_s`), anulată de ack. Raportul se generează apelând modulul D în proces; nu există `PATCH /events/{id}` din automatizare.
- Cu `USE_MOCK=true` emite evenimente false, ca frontend-ul și automatizările să lucreze fără model.
- Endpoint-urile sunt în `docs/contract.md`.

Verificare: `curl localhost:8000/health` răspunde OK, iar `GET /events` întoarce date.

## Run locally

```bash
cd backend
uv sync
PYTHONPATH=.. uv run uvicorn app.main:app --reload --port 8000
# tests
uv run pytest -q
```

`PYTHONPATH=..` makes the repo root importable, so `import automation.report` works once Dalina adds it.

## Run with Docker

From the repo root:

```bash
docker compose up --build
curl localhost:8000/health
```

The image includes `backend/` and `automation/`. The DB and snapshots live in `backend/data/` on the host (ignored by git). `.env` at the repo root is optional; without it the defaults from `app/config.py` apply.
