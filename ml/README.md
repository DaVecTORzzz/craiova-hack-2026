# ml/ — detecție, tracking, zone, FOD, blur

Responsabil: **Andrei**

Brief intern: `safetarmac-docs/01_A_ai_edge.typ` (repo privat).

Primul slice implementat aici este **RESTRICTED_ZONE**: video → YOLO26 → tracking → regulă pe zonă → eveniment valid pentru contract + snapshot blurat. PPE, FOD și fumul vin în PR-uri separate.

## Pornire

```bash
cd ml
uv sync
uv run pytest
```

Rulează fără model și fără backend, pe cadre sintetice:

```bash
uv run python -m safetarmac_ml.run --fake --engine-on --dry-run
cat out/events.jsonl
```

Rulează pe un clip real, cu YOLO26:

```bash
uv sync --extra yolo
./scripts/fetch_face_model.sh
uv run python -m safetarmac_ml.run \
  --source ../data/videos/restricted_zone/<clip>.mp4 \
  --zones fixtures/zones.json \
  --engine-on \
  --dry-run
```

Integrare cu backend-ul, după ce B are rutele de edge:

```bash
uv run python -m safetarmac_ml.run \
  --source ../data/videos/restricted_zone/<clip>.mp4 \
  --engine-on \
  --post \
  --api-url http://localhost:8000 \
  --edge-token "$EDGE_TOKEN"
```

## Ce produce

- `out/events.jsonl` — un eveniment JSON pe linie, exact câmpurile din `docs/contract.md`;
- `out/snapshots/<event_id>.jpg` — cadrul cu fețele blurate;
- un singur eveniment per `(track_id, zone_id, type)` cât timp persoana e în zonă;
- cooldown 10 s după ieșire, apoi reintrarea produce eveniment nou.

## Structura

```text
safetarmac_ml/
  events.py    # EdgeEvent, Confidence, EventContext; fără status/report
  zones.py     # Zone, point_in_polygon, RuleEngine (debounce, cooldown)
  detector.py  # FakeDetector / SyntheticDetector / YoloDetector
  privacy.py   # FaceBlurrer (YuNet) înainte de salvare/upload
  sink.py      # JsonlSink (dry-run) și HttpSink (/edge/snapshots, /edge/events)
  pipeline.py  # cadru -> detecții -> reguli -> eveniment
  run.py       # CLI
fixtures/
  zones.json   # zona engine-left din contract
```

## Reguli

- Punctul de intrare în zonă este **centrul de jos al bbox-ului** (picioarele), nu centrul cutiei.
- `active_when=engine_on` nu emite nimic când motorul e oprit.
- `debounce_s` și confidence temporal: minim 5 cadre observate și 80% confirmare.
- `snapshot_url` e HTTP; niciodată `minio://`.
- `status`, `report`, `received_at`, `notified_at`, `escalated_at`, `acked_at`, `acked_by` nu se trimit din edge.
- Modelul de fețe lipsește → `FaceBlurrer` fail-closed; nu se salvează imagine neblurată.
- `--fake` folosește `NoopBlurrer` doar pentru cadre sintetice, fără fețe.

## Ce nu intră încă

- PPE (vestă, cască, antifoane) și fine-tuning;
- FOD pe cadru de referință;
- VLM pentru fum;
- buffer/retry la pană de conexiune;
- citirea zonelor și `engine_on` din `GET /edge/zones`.

Verificare: `uv run pytest` și `uv run python -m safetarmac_ml.run --fake --engine-on --dry-run`.
