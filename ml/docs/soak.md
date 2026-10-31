# Soak RTSP — 5 minute

Rulat pe 31 octombrie 2026, pe laptopul de demo (AMD Ryzen 7 7840HS, 16 threads, fără GPU discret).

## Setup

- Sursă: clipul `2026-10-30_restricted-zone_cam01_persoana-langa-motor.mp4`, publicat în buclă prin `ml/scripts/rtsp-loop.sh` către `mediamtx`;
- URL: `rtsp://127.0.0.1:8554/stand12`, H.264 1920×1080 30 fps;
- model: `yolo26n.pt` + ByteTrack; blur YuNet;
- zone: `fixtures/zones.stand12.json`, `engine_on=true`;
- transport: `--dry-run`, fără backend, ca soak-ul să testeze doar edge-ul și fluxul RTSP;
- live frame: `--live-dir /tmp/opencode/soak/live`.

## Rezultat

| Element | Valoare |
|---|---|
| Durată țintă | 300 s |
| Durată reală | 300,02 s |
| Cadre procesate | 8.697 |
| FPS end-to-end | 28,99 |
| Evenimente | 64 `RESTRICTED_ZONE` |
| Căderi de flux | 0 |
| Oprire | normală, la `--duration-s 300` |

## Cum se citește

Clipul se reia la nesfârșit, iar pipeline-ul produce aceleași evenimente la fiecare reluare. **64 nu înseamnă 64 de evenimente independente**; sunt peste 30 de reluări ale aceluiași clip, cu 2 evenimente pe reluare. Pentru un soak de stabilitate e ok, pentru rata de falsuri nu.

## Comanda

```bash
podman run --rm -d --replace --name safesight-rtsp -p 8554:8554 bluenviron/mediamtx:latest
./ml/scripts/rtsp-loop.sh

cd ml
uv run python -m safesight_ml.run \
  --source rtsp://127.0.0.1:8554/stand12 \
  --zones fixtures/zones.stand12.json \
  --camera-id stand12 \
  --engine-on \
  --dry-run \
  --duration-s 300 \
  --metrics-json /tmp/opencode/soak/soak.json \
  --out /tmp/opencode/soak/out \
  --live-dir /tmp/opencode/soak/live
```

## Limite

- Nu testează backend-ul, HTTP-ul sau Slack-ul; pentru full stack există run-ul de 200 cadre pe `cam02`.
- Nu testează reconectarea: fluxul nu a căzut, deci nu știm cum se comportă la o întrerupere scurtă.
- Rulat pe laptopul actual, nu pe hardware-ul final de demo.
- Evenimentele sunt repetiții ale aceluiași clip; nu sunt probe independente.
