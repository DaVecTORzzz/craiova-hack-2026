# ml/ — detecție, tracking, zone, FOD, blur

Responsabil: **Andrei**

Brief intern: `safesight-docs/01_A_ai_edge.typ` (repo privat).

Primul slice implementat aici este **RESTRICTED_ZONE**: video → YOLO26 → tracking → regulă pe zonă → eveniment valid pentru contract + snapshot blurat. PPE, FOD și fumul vin în PR-uri separate.

## Pornire

```bash
cd ml
uv sync
uv run pytest
```

Rulează fără model și fără backend, pe cadre sintetice:

```bash
uv run python -m safesight_ml.run --fake --engine-on --dry-run
cat out/events.jsonl
```

Rulează pe un clip real, cu YOLO26:

```bash
uv sync --extra yolo
./scripts/fetch_face_model.sh
uv run python -m safesight_ml.run \
  --source ../data/videos/restricted_zone/<clip>.mp4 \
  --zones fixtures/zones.json \
  --engine-on \
  --dry-run
```

Integrare cu backend-ul, după ce B are rutele de edge:

```bash
uv run python -m safesight_ml.run \
  --source ../data/videos/restricted_zone/<clip>.mp4 \
  --post \
  --remote-config \
  --api-url http://localhost:8000 \
  --edge-token "$EDGE_TOKEN"
```

`--remote-config` ia zonele și `engine_on` din `GET /edge/zones` și le reîmprospătează la 30 s. Dacă backend-ul nu răspunde, folosește `fixtures/zones.json` și flag-ul `--engine-on`.

## Ce produce

- `out/events.jsonl` — un eveniment JSON pe linie, exact câmpurile din `docs/contract.md`;
- `out/snapshots/<event_id>.jpg` — cadrul cu fețele blurate;
- un singur eveniment per `(track_id, zone_id, type)` cât timp persoana e în zonă;
- cooldown 10 s după ieșire, apoi reintrarea produce eveniment nou.

## Structura

```text
safesight_ml/
  events.py    # EdgeEvent, Confidence, EventContext; fără status/report
  zones.py     # Zone, point_in_polygon, RuleEngine (debounce, cooldown)
  detector.py  # FakeDetector / SyntheticDetector / YoloDetector
  privacy.py   # FaceBlurrer (YuNet) înainte de salvare/upload
  sink.py      # JsonlSink (dry-run) și HttpSink (/edge/snapshots, /edge/events)
  pipeline.py  # cadru -> detecții -> reguli -> eveniment
  remote.py    # GET /edge/zones (zone + engine_on)
  run.py       # CLI
fixtures/
  zones.json   # zona engine-left din contract
```

## Reguli

- Punctul de intrare în zonă este **centrul de jos al bbox-ului** (picioarele), nu centrul cutiei.
- `active_when=engine_on` nu emite nimic când motorul e oprit; `--remote-config` ia starea din backend.
- `debounce_s` și confidence temporal: minim 5 cadre observate și 80% confirmare.
- `detected_at` folosește ceasul real al procesării, nu timpul video; `now_s` rămâne pentru durata în zonă.
- `snapshot_url` e HTTP; niciodată `minio://`. Snapshot-ul se urcă cu `event_id` ca form field.
- `FaceBlurrer` blurează fețele YuNet **și** partea de sus a fiecărui bbox de persoană, ca plasă de siguranță pentru fețe mici.
- Stările track-urilor dispărute se curăță după cooldown.
- `status`, `report`, `received_at`, `notified_at`, `escalated_at`, `acked_at`, `acked_by` nu se trimit din edge.
- Modelul de fețe lipsește → `FaceBlurrer` fail-closed; nu se salvează imagine neblurată.
- `--fake` folosește `NoopBlurrer` doar pentru cadre sintetice, fără fețe.

## Ce nu intră încă

- PPE (vestă, cască, antifoane) și fine-tuning;
- FOD pe cadru de referință;
- VLM pentru fum;
- buffer/retry la pană de conexiune;
- citirea zonelor și `engine_on` din `GET /edge/zones`.

Verificare: `uv run pytest` și `uv run python -m safesight_ml.run --fake --engine-on --dry-run`.
