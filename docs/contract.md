# Contractul dintre module

Versiunea 1. Pornește de la brief-ul de frontend (rolul C). Responsabil de contract: Max (backend). Orice schimbare se face prin pull request aprobat de cel afectat.

## Evenimentul

```json
{
  "event_id": "evt_0142",
  "type": "RESTRICTED_ZONE",
  "severity": "CRITICAL",
  "status": "open",
  "camera_id": "stand12",
  "zone_id": "engine-left",
  "track_id": 17,
  "timestamp": "2026-11-01T10:42:13Z",
  "duration_s": 1.4,
  "confidence": { "detector": 0.91, "temporal": "14/15 cadre" },
  "context": { "engine_on": true },
  "snapshot": "/snapshots/evt_0142.jpg",
  "model": "person-ppe-v1",
  "report": null,
  "notified_at": null,
  "escalated_at": null,
  "acknowledged_by": null
}
```

| Câmp | Valori |
|---|---|
| `type` | `RESTRICTED_ZONE`, `NO_PPE`, `FOD`, `SMOKING`, `CAMERA_OFFLINE` (`CROWD` e planificat) |
| `severity` | `CRITICAL`, `WARNING`, `RESOLVED` |
| `status` | `open`, `verifying` (ex. fumat în curs de confirmare), `escalated`, `acknowledged`, `false_positive` |
| `confidence.detector` | scorul detectorului, 0–1 |
| `confidence.temporal` | câte cadre din ultimele N au confirmat încălcarea, ca text |
| `snapshot` | cale relativă la backend; imaginea e deja blurată |
| `report` | `null` până scrie automatizarea raportul; apoi `{ what, where, when, severity_reason, recommended_action }` |
| `acknowledged_by` | numele operatorului trimis de interfață (nu există login în demo) |

Interfața nu afișează niciodată nume de persoane, doar `track_id` („persoana #17”).

## Endpoint-uri

| Metodă | Endpoint | Cine îl folosește | Rol |
|---|---|---|---|
| GET | `/cameras` | frontend | lista camerelor |
| GET | `/stream/{camera_id}.mjpg` | frontend | video adnotat și blurat |
| GET | `/zones?camera_id=stand12` | frontend, ml | zonele unei camere |
| PUT | `/zones/{zone_id}` | frontend | salvează o zonă |
| POST | `/zones/reference-frame` | frontend | salvează cadrul de referință pentru FOD |
| GET | `/events?status=open&severity=CRITICAL` | frontend | lista de evenimente |
| GET | `/events/{event_id}` | frontend | detaliul unui incident |
| POST | `/events/{event_id}/ack` | frontend, automation | confirmare; body `{ "operator": "Ana" }` |
| POST | `/events/{event_id}/false-positive` | frontend, automation | alarmă falsă; body `{ "operator": "Ana" }` |
| POST | `/events/{event_id}/reopen` | frontend | redeschide |
| POST | `/events/{event_id}/regenerate-report` | frontend | cere un raport nou |
| PATCH | `/events/{event_id}` | automation | scrie `report`, `notified_at`, `escalated_at`, `status` |
| GET | `/context` | frontend | starea motorului per cameră |
| POST | `/context/engine` | frontend (doar demo) | `{ "camera_id": "stand12", "engine_on": true }` |
| GET | `/kpi` | frontend | conformitate PPE, incidente deschise, latență, escaladate |
| GET | `/reports?shift=morning&date=2026-10-30` | frontend | raportul de tură, inclusiv rezumatul |
| WS | `/ws/events` | frontend | evenimente în timp real |

Mesajele WebSocket: `{"type": "event.created" | "event.updated" | "context.updated", "data": { ... }}`. Pentru evenimente, `data` e evenimentul complet.

## Zona

```json
{
  "zone_id": "engine-left",
  "camera_id": "stand12",
  "rule": "RESTRICTED",
  "points": [[0.46, 0.16], [0.76, 0.16], [0.76, 0.68], [0.46, 0.68]],
  "active_when": "engine_on",
  "required_ppe": [],
  "severity": "CRITICAL",
  "min_seconds": 1.0,
  "notify": "slack",
  "escalate_after_s": 120
}
```

- `rule`: `PPE_REQUIRED`, `RESTRICTED`, `FOD_WATCH`, `NO_SMOKING`
- `active_when`: `always`, `engine_on`, `schedule`
- `points`: coordonate normalizate 0–1 față de cadru, nu pixeli

## ml → backend (în același proces Python)

```python
@dataclass
class FrameResult:
    camera_id: str
    frame: np.ndarray        # cadru adnotat și blurat (pentru MJPEG)
    raw_frame: np.ndarray    # cadru blurat, fără adnotări (pentru snapshot)
    people: list[Person]     # track_id, bbox, zone_ids, missing_ppe, confidence
    fod: list[FodObject]     # bbox, static_seconds
    smoking: list[SmokeHit]  # track_id, bbox, confidence
```

## backend → automation

`automation.on_event_created(event: dict) -> None`, apelat de backend la fiecare eveniment nou. Automatizarea răspunde prin `PATCH /events/{event_id}`.

## De confirmat în echipă

- Snapshot-urile stau pe disc (simplu) sau în MinIO (brief-ul propune `minio://`)?
- Modelul Groq exact: verificați în consola Groq ID-ul curent (`openai/gpt-oss-120b` sau înlocuitorul recomandat).
