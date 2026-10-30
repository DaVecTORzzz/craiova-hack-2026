# backend/ — API, rule engine, stream, stocare

Responsabil: **Max**

- FastAPI + Uvicorn, Pydantic v2, SQLite prin SQLModel. Postgres doar plan B, cu aceeași schemă.
- Ingestie edge: `POST /edge/events` idempotent după `event_id`; `POST /edge/snapshots`; `GET /edge/zones` cu `X-Edge-Token`.
- Rule engine: debounce per `(track_id, zone_id, type)`, un singur eveniment per track, cooldown, context `engine_on`, severitate.
- Stream MJPEG pe `/stream/{camera_id}.mjpg`, WebSocket pe `/ws/events` doar cu `event.created` și `event.updated`.
- Acțiuni operator: ack, fals pozitiv, reopen; fiecare intră în `event_actions` cu operator și momentul acțiunii.
- Escaladare per zonă (`escalate_after_s`), anulată de ack. Raportul se generează apelând modulul D în proces; nu există `PATCH /events/{id}` din automatizare.
- Cu `USE_MOCK=true` emite evenimente false, ca frontend-ul și automatizările să lucreze fără model.
- Endpoint-urile sunt în `docs/contract.md`.

Verificare: `curl localhost:8000/health` răspunde OK, iar `GET /events` întoarce date.
