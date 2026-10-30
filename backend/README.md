# backend/ — API, rule engine, stream, stocare

Responsabil: **Max**

- FastAPI + Uvicorn, Pydantic v2, SQLite.
- Rule engine: debounce per `(track_id, zone_id, type)`, un singur eveniment per track, cooldown, context `engine_on`, severitate.
- Stream MJPEG pe `/stream/{camera_id}.mjpg`, WebSocket pe `/ws/events`.
- Cu `USE_MOCK=true` emite evenimente false, ca frontend-ul și automatizările să lucreze fără model.
- Endpoint-urile sunt în `docs/contract.md`.

Verificare: `curl localhost:8000/health` răspunde OK, iar `GET /events` întoarce date.
