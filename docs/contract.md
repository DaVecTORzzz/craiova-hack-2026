# Contractul dintre module

Versiunea 2 · 30 octombrie 2026. Aliniat la briefingurile Ultra A–D. Responsabil: Max (backend). Orice schimbare se face prin pull request aprobat de cel afectat.

Contractul are două fețe: ce trimite edge-ul (A) și ce întoarce backend-ul (B). C consume doar forma returnată de B. Un câmp care nu apare aici nu se inventează în alt modul.

## Evenimentul trimis de edge (A → B)

```json
{
  "event_id": "evt_stand12_1793356933120_17",
  "type": "RESTRICTED_ZONE",
  "severity": "CRITICAL",
  "camera_id": "stand12",
  "zone_id": "engine-left",
  "track_id": 17,
  "confidence": { "detector": 0.91, "temporal": { "seen": 14, "window": 15 } },
  "duration_s": 1.4,
  "context": { "engine_on": true },
  "snapshot_url": "/snapshots/evt_stand12_1793356933120_17.jpg",
  "model": "person-ppe-v1",
  "detected_at": "2026-10-30T10:42:13.120Z"
}
```

Edge **nu** trimite `status`, `report`, `received_at`, `notified_at`, `escalated_at`, `acked_at` sau `acked_by`. Acestea sunt câmpuri de backend; un payload care le conține se respinge cu `422`.

| Câmp | Tip | Regulă |
|---|---|---|
| `event_id` | string | `evt_<camera_id>_<unix_ms>_<track_id>`; unic, cheia de idempotență. |
| `type` | enum | `RESTRICTED_ZONE`, `NO_PPE`, `FOD`, `SMOKING`, `CAMERA_OFFLINE`. `CROWD` e rezervat. |
| `severity` | enum | Doar `CRITICAL` sau `WARNING`. `RESOLVED` este status, nu severitate. |
| `camera_id` | string | ID-ul din seed: `stand12`, `taxiway-b`, `baggage-area`. |
| `zone_id` | string | ID-ul zonei din seed sau din editorul lui C. |
| `track_id` | int | ID ByteTrack. `0` pentru evenimente fără track de persoană (FOD, cameră offline). |
| `confidence` | object | `{ detector: 0–1, temporal: { seen, window } }`. Nu șir, nu float simplu. |
| `duration_s` | float | Timpul în zonă sau al obiectului static. |
| `context` | object | `{ engine_on: bool }` la momentul detecției. |
| `snapshot_url` | string | URL HTTP relativ, servit de `GET /snapshots/{file}`. Niciodată `minio://`. |
| `model` | string | Nume și versiune, ex. `person-ppe-v1`. |
| `detected_at` | string | ISO 8601 UTC, cu milisecunde. |

## Evenimentul returnat de backend (B → C)

```json
{
  "event_id": "evt_stand12_1793356933120_17",
  "type": "RESTRICTED_ZONE",
  "severity": "CRITICAL",
  "status": "open",
  "camera_id": "stand12",
  "zone_id": "engine-left",
  "track_id": 17,
  "confidence": { "detector": 0.91, "temporal": { "seen": 14, "window": 15 } },
  "duration_s": 1.4,
  "context": { "engine_on": true },
  "snapshot_url": "/snapshots/evt_stand12_1793356933120_17.jpg",
  "model": "person-ppe-v1",
  "detected_at": "2026-10-30T10:42:13.120Z",
  "received_at": "2026-10-30T10:42:13.310Z",
  "notified_at": "2026-10-30T10:42:14.920Z",
  "escalated_at": null,
  "acked_at": null,
  "acked_by": null,
  "report": {
    "what": "Persoană în zona motorului stâng, cu motorul pornit.",
    "where": "Stand 12, zona engine-left.",
    "when": "10:42:13, timp în zonă 1,4 s.",
    "severity_reason": "Motorul e pornit; risc de ingestie sau jet blast.",
    "recommended_action": "Oprește activitatea la Stand 12. Contactează persoana prin radio.",
    "source": "llm"
  }
}
```

| Câmp | Sursă | Regulă |
|---|---|---|
| `status` | B | `open` la ingestie; apoi `acknowledged`, `false_positive`, `escalated` sau `resolved`. |
| `received_at` | B | Momentul validării. `received_at − detected_at` = latența de ingestie. |
| `notified_at` | B | Momentul în care Slack a acceptat mesajul; `null` dacă notificarea a eșuat. |
| `escalated_at` | B | Momentul escaladării; `null` dacă operatorul a confirmat la timp. |
| `acked_at`, `acked_by` | B | Operatorul și momentul confirmării; se copiază și în `event_actions`. |
| `report` | B + D | Cele cinci câmpuri + `source` (`llm` sau `template`); `null` până la generare. |

Nu există status intermediar `verifying`. Fumul este stretch și se emite doar după răspunsul VLM; dacă VLM-ul nu confirmă, nu există eveniment.

## Endpoint-uri

### Edge → backend

| Metodă | Endpoint | Rol | Auth |
|---|---|---|---|
| POST | `/edge/events` | ingestie eveniment; idempotentă după `event_id` | `X-Edge-Token` |
| POST | `/edge/snapshots` | upload JPEG; întoarce `snapshot_url` HTTP | `X-Edge-Token` |
| GET | `/edge/zones?camera_id=stand12` | zone active, `engine_on`, `config_version`; poll la 30 s | `X-Edge-Token` |

### Frontend → backend

| Metodă | Endpoint | Rol |
|---|---|---|
| GET | `/cameras` | camere, `rtsp_url`, `online`, `engine_on` |
| PUT | `/cameras/{camera_id}/engine` | setează `engine_on`; body `{ "on": true }`; doar demo |
| GET | `/zones?camera_id=stand12` | zonele pentru editor |
| PUT | `/zones/{zone_id}` | salvează zona; A o reîncarcă fără restart |
| POST | `/zones/reference-frame` | salvează cadrul de referință pentru FOD |
| GET | `/events?status=open&severity=CRITICAL` | lista de evenimente, filtre combinabile |
| GET | `/events/{event_id}` | detaliu: dovadă, cronologie, raport |
| POST | `/events/{event_id}/ack` | confirmare; body `{ "operator": "Ana" }` |
| POST | `/events/{event_id}/false-positive` | fals pozitiv; body `{ "operator": "Ana", "note": "..." }` |
| POST | `/events/{event_id}/reopen` | redeschide; repornește timerul |
| POST | `/events/{event_id}/regenerate-report` | regenerează raportul (LLM sau șablon) |
| GET | `/reports?shift=morning&date=2026-10-30` | raportul de tură, inclusiv rezumatul |
| GET | `/kpi?date=2026-10-30&shift=morning` | PPE, incidente deschise, latență, escaladări |
| GET | `/snapshots/{file}` | imaginea, deja blurată; HTTP, niciodată `minio://` |
| GET | `/stream/{camera_id}.mjpg` | video adnotat MJPEG; plan B: snapshot la 500 ms |
| WS | `/ws/events` | doar `event.created` și `event.updated` |
| GET | `/health` | stare API, DB și worker edge |

Mesajele WebSocket: `{"type": "event.created" | "event.updated", "data": { ...eveniment complet... }}`. Nu există `context.updated`; starea motorului se citește din `GET /cameras`, iar KPI din `GET /kpi` la 5 s.

## Zona

```json
{
  "id": "engine-left",
  "camera_id": "stand12",
  "name": "Motor stâng",
  "rule_type": "RESTRICTED",
  "active_when": "engine_on",
  "required_ppe": [],
  "severity": "CRITICAL",
  "debounce_s": 1.0,
  "escalate_after_s": 30,
  "notify_channel": "slack",
  "polygon": [[0.46, 0.16], [0.76, 0.16], [0.76, 0.68], [0.46, 0.68]],
  "reference_frame": null
}
```

- `rule_type`: `RESTRICTED`, `PPE_REQUIRED`, `FOD_WATCH`, `NO_SMOKING`; `CROWD_WATCH` rezervat.
- `active_when`: `always`, `engine_on`; `schedule` rămâne roadmap.
- `polygon`: coordonate normalizate 0–1 față de cadru, nu pixeli.
- `debounce_s`: durata minimă în zonă. FOD: `3` în demo, `10` în producție.
- `escalate_after_s`: per zonă; `null` = fără escaladare. Seed demo `30`, producție `120`.
- `notify_channel`: `slack` în demo; Teams/SMS/radio rămân roadmap.

## A → B: snapshot și eveniment

1. A decodează cadrul, rulează detecția și tracking-ul, aplică regula pe zonă.
2. A blurează fețele **înainte** de orice salvare sau upload.
3. A face `POST /edge/snapshots` și primește `snapshot_url`.
4. A face `POST /edge/events` cu payload-ul de mai sus.
5. B validează, salvează, emite `event.created`, trimite Slack și pornește raportul.

`FrameResult` este un tip intern al lui A; nu traversează granița dintre module. Pentru demo, A și B pot rula în același container, dar contractul rămâne HTTP.

## B → D: raportul

B apelează `automation.report.generate(event)` în proces, nu printr-un endpoint. Modulul D primește evenimentul, alege acțiunea din tabelul fix pe tip și cere LLM-ului doar reformularea. Rezultatul se scrie în `report_texts`, iar B emite `event.updated`.

- Model: Groq `llama-3.3-70b-versatile`, mod JSON, temperatură 0,2.
- Fallback: șablonul completează aceleași câmpuri din JSON, cu `source=template`.
- `POST /events/{event_id}/regenerate-report` există doar pentru C; nu înlocuiește apelul în proces al lui B.
- Notificarea Slack pleacă imediat, cu text + link, fără să aștepte raportul.

## Decizii canonicate

- `event_id`, nu `id`; `snapshot_url`, nu `snapshot` sau `minio://`.
- `confidence` este obiect, nu șir „14/15 cadre”.
- Severitate doar `CRITICAL` / `WARNING`; `RESOLVED` este status.
- Statusuri: `open`, `acknowledged`, `false_positive`, `escalated`, `resolved`.
- SQLite prin SQLModel; Postgres doar plan B.
- Slack incoming webhook, text + link, fără imagini și fără butoane.
- Escaladare per zonă; FOD 3 s demo / 10 s producție.
- Demo fără login: câmp `operator`; JWT/SSO și audit sunt roadmap.
- Groq pentru raport, Claude Haiku pentru VLM (stretch).
- B apelează modulul D în proces; nu există `PATCH /events/{id}` din automatizare.

## Decizii tehnice

- **Model de detecție: YOLO26.** Nu YOLO11 și nu generații mai vechi. `YOLO26s` pentru acuratețe, `YOLO26n` dacă FPS-ul scade sub 10. `YOLO11s` rămâne doar fallback dacă YOLO26 nu converge pe PPE/FOD sau nu exportă pe edge; orice schimbare se anunță înainte de demo.
- Licența YOLO și datele FOD-A se verifică înainte de orice demo comercial.
