# Benchmark — edge

Testarea pe toate cele 6 clipuri, inclusiv B-roll și full stack pe `cam02`, este în [`clip-tests.md`](clip-tests.md). Soak-ul RTSP de 5 minute este în [`soak.md`](soak.md), iar eșantionul de falsuri în [`false-alarms.md`](false-alarms.md). Fișierul de față rămâne benchmark-ul detaliat pentru cazul de demo `cam01`.

Măsurat pe 31 octombrie 2026, pe laptopul de demo: **AMD Ryzen 7 7840HS with Radeon 780M, 8 core-uri / 16 threads, fără GPU discret**.

| Element | Valoare |
|---|---|
| Hardware | AMD Ryzen 7 7840HS with Radeon 780M, 8C/16T, fără GPU discret |
| Model | `yolo26n.pt` |
| Sursă | `2026-10-30_restricted-zone_cam01_persoana-langa-motor.mp4`, 1920×1080 |
| Cadre procesate | 120 |
| Timp total | **6,86 s median** (3 rulări; include pornirea Python și încărcarea modelului) |
| FPS end-to-end | **~17,5** (median, cu startup) |
| Procesare pură | **5,71 s median, ~21,0 FPS** (fără startup) |
| Evenimente | **1** (track 3), `RESTRICTED_ZONE` |
| Confidence detector | 0,55 |
| Ingestie la backend | 135–162 ms (`received_at − detected_at`) |
| Debounce în demo | 0,5 s; evenimentele au ieșit la 0,50–0,57 s |
| Live frame | 1920×1080, scris în `live/stand12.jpg` |
| Blur | YuNet + top 35% din bbox; fețele din snapshot sunt blurate |

## Cum s-a măsurat

```bash
cd ml
uv sync --extra yolo
./scripts/fetch_face_model.sh
/usr/bin/time -f 'elapsed=%e s' uv run python -m safesight_ml.run \
  --source ../data/videos/2026-10-30_restricted-zone_cam01_persoana-langa-motor.mp4 \
  --zones fixtures/zones.stand12.json \
  --engine-on \
  --dry-run \
  --max-frames 120 \
  --metrics-json out/bench.json
```

Pentru integrare, același run cu `--post --api-url http://127.0.0.1:8001 --edge-token dev-edge-token`.

## Protocol de 3 rulări

Trei rulări consecutive, dry-run, 120 cadre, același clip și aceleași zone. `wall` include pornirea Python și încărcarea modelului; `processing` este timpul raportat de `metrics.json`.

| Run | Wall | FPS wall | Processing | FPS processing | Evenimente |
|---|---:|---:|---:|---:|---:|
| 1 | 6,89 s | 17,4 | 5,71 s | 21,0 | 1 |
| 2 | 6,86 s | 17,5 | 5,74 s | 20,9 | 1 |
| 3 | 6,67 s | 18,0 | 5,54 s | 21,7 | 1 |
| **Median** | **6,86 s** | **17,5** | **5,71 s** | **21,0** | **1** |

Pentru pitch folosește medianul, nu o singură rulare. Dacă demo-ul rulează pe alt laptop, remăsoară pe acela.

Pentru reproducere, rulează aceeași comandă de trei ori:

```bash
for i in 1 2 3; do
  /usr/bin/time -f "run=$i wall=%e s" \
    uv run python -m safesight_ml.run \
    --source ../data/videos/2026-10-30_restricted-zone_cam01_persoana-langa-motor.mp4 \
    --zones fixtures/zones.stand12.json \
    --camera-id stand12 --engine-on --dry-run --max-frames 120 \
    --metrics-json "out/bench-$i.json"
done
```

Nu am făcut warm-up separat; prima rulare poate fi mai lentă din cauza cache-ului.

## RTSP local (mediamtx)

Măsurat pe 31 octombrie 2026, cu clipul din demo publicat în buclă prin `ml/scripts/rtsp-loop.sh`.

| Element | Valoare |
|---|---|
| Sursă | `rtsp://127.0.0.1:8554/stand12`, H.264 1920×1080 30 fps |
| Cadre | 120 |
| Timp end-to-end | 9,34 s |
| Evenimente | 2 `RESTRICTED_ZONE` (măsurat înainte de poligonul #41; de remăsurat) |
| Config | `--remote-config` activ |
| Live frame | `/stream/stand12.mjpg` a servit exact cadrul scris de edge |

Comanda completă este în `ml/README.md`, secțiunea „RTSP real, pentru demo”. Pentru soak și metrics:

```bash
uv run python -m safesight_ml.run --source rtsp://127.0.0.1:8554/stand12 \
  --camera-id stand12 --remote-config --post --duration-s 300 \
  --metrics-json out/soak.json --api-url http://localhost:8000 --edge-token "$EDGE_TOKEN"
```

## Ce nu e măsurat încă

- Rata de falsuri alarme pe 50–100 evenimente etichetate.
- Reconectarea RTSP după o cădere scurtă; soak-ul de 5 minute e deja în `soak.md`.
- FPS pe Jetson / hardware de pilot.
- PPE și FOD: nu există clipuri, iar codul de detecție pentru ele nu e implementat (există doar adnotări preliminare).

## Observații

- Confidence-ul de 0,55 e aproape de pragul 0,35; pentru demo, verifică luminarea și pragul înainte de pitch.
- Poligonul calibrat este în `fixtures/zones.stand12.json`; backend-ul are încă poligonul vechi în seed, deci pentru `--remote-config` actualizează zona prin UI/`PUT /zones/engine-left` sau folosește `--zones`.
- Rezultatul e pe CPU; cu GPU-ul din dotare, FPS-ul poate fi mai mare, dar se măsoară din nou.
