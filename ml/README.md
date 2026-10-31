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

Rulează pe clipul real, cu YOLO26:

```bash
uv sync --extra yolo
./scripts/fetch_face_model.sh
uv run python -m safesight_ml.run \
  --source ../data/videos/2026-10-30_restricted-zone_cam01_persoana-langa-motor.mp4 \
  --zones fixtures/zones.stand12.json \
  --camera-id stand12 \
  --engine-on \
  --dry-run \
  --live-dir ../backend/snapshots/live
```

`fixtures/zones.stand12.json` are poligonul calibrat pe clip. `--live-dir` scrie `live/stand12.jpg`, pe care backend-ul îl servește la `/stream/stand12.mjpg`. Cu Docker, calea este `../backend/data/snapshots/live`.

Integrare cu backend-ul:

```bash
uv run python -m safesight_ml.run \
  --source ../data/videos/2026-10-30_restricted-zone_cam01_persoana-langa-motor.mp4 \
  --zones fixtures/zones.stand12.json \
  --camera-id stand12 \
  --engine-on \
  --post \
  --live-dir ../backend/snapshots/live \
  --api-url http://localhost:8000 \
  --edge-token "$EDGE_TOKEN"
```

`--remote-config` ia zonele și `engine_on` din `GET /edge/zones` și le reîmprospătează la 30 s. Dacă backend-ul nu răspunde, folosește `fixtures/zones.stand12.json` și flag-ul `--engine-on`. Pentru `--remote-config`, zona din backend trebuie să aibă poligonul calibrat; altfel folosește `--zones`.

## RTSP real, pentru demo

Pornește un server RTSP local (o singură dată; imaginea se descarcă prima dată):

```bash
podman run --rm -d --replace --name safesight-rtsp -p 8554:8554 bluenviron/mediamtx:latest
```

Publică un clip în buclă, într-un terminal separat:

```bash
cd ml
./scripts/rtsp-loop.sh
# sau: ./scripts/rtsp-loop.sh ../data/videos/<clip>.mp4 rtsp://127.0.0.1:8554/stand12
```

Rulează edge-ul pe fluxul RTSP, nu pe fișier:

```bash
uv run python -m safesight_ml.run \
  --source rtsp://127.0.0.1:8554/stand12 \
  --camera-id stand12 \
  --remote-config \
  --post \
  --live-dir ../backend/snapshots/live \
  --api-url http://localhost:8000 \
  --edge-token "$EDGE_TOKEN"
```

`--live-dir` trebuie să fie exact `SNAPSHOT_DIR/live` al backend-ului: implicit local `../backend/snapshots/live`, iar cu Docker `../backend/data/snapshots/live`. Dacă folosești alt `SNAPSHOT_DIR`, schimbă și aici, altfel `/stream` servește placeholder-ul.

Oprește serverul după demo:

```bash
podman rm -f safesight-rtsp
```

Verificat local pe 31 octombrie 2026: 120 de cadre citite din `rtsp://127.0.0.1:8554/stand12` în 9,34 s end-to-end, 2 evenimente `RESTRICTED_ZONE`, `--remote-config` activ, iar `/stream/stand12.mjpg` a servit exact cadrul scris de edge. Dacă backend-ul nu răspunde, edge-ul folosește `fixtures/zones.stand12.json` și `--engine-on`.

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
  live.py      # ultimul cadru blurat pentru /stream MJPEG
  pipeline.py  # cadru -> detecții -> reguli -> eveniment
  remote.py    # GET /edge/zones (zone + engine_on)
  run.py       # CLI
fixtures/
  zones.json          # zona engine-left din contract
  zones.stand12.json  # poligon calibrat pe clipul real
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
- rata de falsuri alarme, măsurată pe 50–100 evenimente;
- reconectare automată la căderea fluxului RTSP (acum procesul se oprește la primul `read()` eșuat).

Verificare: `uv run pytest` (31 teste) și `uv run python -m safesight_ml.run --fake --engine-on --dry-run`. Cifrele reale sunt în [`docs/benchmark.md`](docs/benchmark.md).
