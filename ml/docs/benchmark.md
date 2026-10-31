# Benchmark — edge

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

## Ce nu e măsurat încă

- Rata de falsuri alarme pe 50–100 evenimente etichetate.
- FPS pe un flux RTSP real, nu pe fișier.
- FPS pe Jetson / hardware de pilot.
- PPE și FOD, pentru că nu există încă clipuri/adnotări.

## Observații

- Confidence-ul de 0,40–0,55 e aproape de pragul 0,35; pentru demo, verifică luminarea și pragul înainte de pitch.
- Poligonul calibrat este în `fixtures/zones.stand12.json`; backend-ul are încă poligonul vechi în seed, deci pentru `--remote-config` actualizează zona prin UI/`PUT /zones/engine-left` sau folosește `--zones`.
- Rezultatul e pe CPU; cu GPU-ul din dotare, FPS-ul poate fi mai mare, dar se măsoară din nou.
