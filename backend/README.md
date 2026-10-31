# backend/ — API, stream, stocare

Responsabil: **Max**

Brief intern: `safesight-docs/02_B_backend.typ` (repo privat).

- FastAPI + Uvicorn, Pydantic v2, SQLite prin SQLModel. Postgres doar plan B, cu aceeași schemă.
- Ingestie edge: `POST /edge/events` idempotent după `event_id`; `POST /edge/snapshots`; `GET /edge/zones` cu `X-Edge-Token`.
- Rule engine-ul (debounce, fereastră temporală, cooldown, un eveniment per prezență) rulează pe edge, în `ml/`. Backend-ul primește evenimente deja confirmate și le validează după contract.
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

## Demo fallback

If the edge, the camera or the model fails during the demo, send the demo event by hand. It uses the same routes as the edge, so Live, the incident page, Slack and escalation work as usual.

```bash
cd backend
uv run python scripts/demo_event.py                 # RESTRICTED_ZONE on stand12 / engine-left, engine turned on first
uv run python scripts/demo_event.py --type FOD      # or NO_PPE
```

`--api-url` and `--edge-token` default to `API_URL` / `EDGE_TOKEN` or `http://localhost:8000` / `dev-edge-token`. Without `--snapshot` it uploads a synthetic gray frame; with `--snapshot` pass only an already-blurred JPEG.
