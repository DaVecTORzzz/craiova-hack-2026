# Benchmark — edge

Testarea pe toate cele 6 clipuri, inclusiv B-roll și full stack pe `cam02`, este în [`clip-tests.md`](clip-tests.md). Soak-ul RTSP de 5 minute este în [`soak.md`](soak.md), iar eșantionul de falsuri în [`false-alarms.md`](false-alarms.md). Fișierul de față rămâne benchmark-ul detaliat pentru cazul de demo `cam01`.

Măsurat pe 31 octombrie 2026, pe laptopul de demo.

| Element | Valoare |
|---|---|
| Hardware | AMD Ryzen 7 7840HS, 16 threads, fără GPU discret |
| Model | `yolo26n.pt` |
| Sursă | `2026-10-30_restricted-zone_cam01_persoana-langa-motor.mp4`, 1920×1080 |
| Cadre procesate | 120 |
| Timp total | 6,94 s (end-to-end, inclusiv pornirea Python și încărcarea modelului) |
| FPS end-to-end | ~17,3 |
| Evenimente | 2 (track 3 și 4), ambele `RESTRICTED_ZONE` |
| Confidence detector | 0,40–0,55 |
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
  --max-frames 120
```

Pentru integrare, același run cu `--post --api-url http://127.0.0.1:8001 --edge-token dev-edge-token`.

## Măsurători repetate

Re-măsurat pe 31 octombrie 2026, dry-run, fără live/post, pe același clip de 120 cadre: **5,39 s end-to-end, ~22,3 FPS**. Prima inferență încălzește modelul, iar valoarea variază cu încărcarea mașinii; pentru pitch folosește cifra măsurată pe hardware-ul de demo, nu o medie între rulări.

## RTSP local (mediamtx)

Măsurat pe 31 octombrie 2026, cu clipul din demo publicat în buclă prin `ml/scripts/rtsp-loop.sh`.

| Element | Valoare |
|---|---|
| Sursă | `rtsp://127.0.0.1:8554/stand12`, H.264 1920×1080 30 fps |
| Cadre | 120 |
| Timp end-to-end | 9,34 s |
| Evenimente | 2 `RESTRICTED_ZONE` |
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

- Confidence-ul de 0,40–0,55 e aproape de pragul 0,35; pentru demo, verifică luminarea și pragul înainte de pitch.
- Poligonul calibrat este în `fixtures/zones.stand12.json`; backend-ul are încă poligonul vechi în seed, deci pentru `--remote-config` actualizează zona prin UI/`PUT /zones/engine-left` sau folosește `--zones`.
- Rezultatul e pe CPU; cu GPU-ul din dotare, FPS-ul poate fi mai mare, dar se măsoară din nou.
