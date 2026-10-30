# backend/ — API, rule engine, stream, stocare

Responsabil: **Max**

Brief intern: `safetarmac-docs/02_B_backend.typ` (repo privat).

- FastAPI + Uvicorn, Pydantic v2, SQLite prin SQLModel. Postgres doar plan B, cu aceeași schemă.
- Ingestie edge: `POST /edge/events` idempotent după `event_id`; `POST /edge/snapshots`; `GET /edge/zones` cu `X-Edge-Token`.
- Rule engine: debounce per `(track_id, zone_id, type)`, un singur eveniment per track, cooldown, context `engine_on`, severitate.
- Stream MJPEG pe `/stream/{camera_id}.mjpg`, WebSocket pe `/ws/events` doar cu `event.created` și `event.updated`.
- Login cu roluri (JWT): `operator`, `supervisor`, `admin`. Acțiunile operatorului (ack, fals pozitiv, reopen) intră în `event_actions` și în `audit_log`, cu utilizatorul din token.
- Planul de implementare pas cu pas: [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md).
- Escaladare per zonă (`escalate_after_s`), anulată de ack. Raportul se generează apelând modulul D în proces; nu există `PATCH /events/{id}` din automatizare.
- Cu `USE_MOCK=true` emite evenimente false, ca frontend-ul și automatizările să lucreze fără model.
- Endpoint-urile sunt în `docs/contract.md`.

Verificare: `curl localhost:8000/health` răspunde OK, iar `GET /events` întoarce date.
