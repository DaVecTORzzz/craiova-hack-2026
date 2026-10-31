# Teste pe clipuri — 31 octombrie 2026

Testare pe toate cele 6 clipuri din `data/videos/`, cu modelul real și poligonul calibrat pentru `stand12`. Rezultatele sunt măsurători de laborator, nu promisiuni de producție.

Soak-ul RTSP de 5 minute este în [`soak.md`](soak.md); inventarul celor 4 evenimente reale este în [`false-alarms.md`](false-alarms.md).

## Metodă

- Hardware: AMD Ryzen 7 7840HS, 16 threads, fără GPU discret.
- Model: `yolo26n.pt` + ByteTrack; blur: YuNet.
- Zone: `ml/fixtures/zones.stand12.json`; `engine_on=true`; `--dry-run`, fără backend.
- Fiecare clip a fost rulat integral; FPS-ul este end-to-end, inclusiv prima inferență, fără timpul de încărcare a modelului.
- Pentru B-roll, poligonul `stand12` nu este calibrat pe imaginea lor; rezultatele B-roll sunt dinainte de poligonul #41 și rămân doar smoke. Evenimentele de acolo sunt un *smoke de zonă*, nu o rată de falsuri alarme.

## Rezultate

| Clip | Rezoluție | Cadre | Evenimente | FPS | Confidence | Observații |
|---|---|---:|---:|---:|---|---|
| `broll_cam01_marshaller-conuri-apron` | 1280×720 | 366 | 1 | 32,7 | 0,37 | poligon stand12 aplicat pe B-roll; nu e caz de demo |
| `broll_cam02_avion-la-poarta-bagaje` | 3840×2160 | 318 | 5 | 23,4 | 0,35–0,80 | poligon stand12 aplicat pe B-roll; nu e caz de demo |
| `broll_cam03_lucratori-cu-veste-apron` | 2160×3840 | 886 | 12 | 27,0 | 0,35–0,55 | poligon stand12 aplicat pe B-roll; nu e caz de demo |
| `broll_cam04_tractor-bagaje-apron` | 1920×1080 | 928 | 1 | 36,5 | 0,38 | poligon stand12 aplicat pe B-roll; nu e caz de demo |
| `restricted-zone_cam01_persoana-langa-motor` | 1920×1080 | 263 | 1 | 28,9 | 0,55 | poligonul #41; cazul validat pentru demo |
| `restricted-zone_cam02_lucratori-pushback-motor` | 3840×2160 | 200 | 3 | 20,0 | 0,44–0,75 | al doilea caz real; poligonul nu e calibrat pe cam02 |

Pentru comparație, eșantionul de 120 cadre din `cam01` din [`benchmark.md`](benchmark.md) are median **~17,5 FPS wall** (6,86 s, cu pornirea Python și modelul) și **~21,0 FPS processing**. Diferența față de rularea integrală vine din pornire, din prima inferență și din încălzirea modelului.

## Ce arată rezultatele

- Ambele clipuri `restricted-zone` produc evenimente: **1** pe `cam01`, **3** pe `cam02`.
- `cam01` este cazul validat cap-coadă: eveniment, snapshot blurat, ingestie backend, live frame.
- `cam02` confirmă că pipeline-ul generalizează pe al doilea unghi, dar poligonul trebuie recalibrat înainte de a fi folosit ca demo.
- B-roll-ul cu poligonul `stand12` produce alarme; asta nu este o rată de falsuri, ci dovada că o zonă greșită mută problema. Pentru rata reală de falsuri trebuie poligon calibrat pe fiecare cameră și etichetare manuală.

## Full stack pe `cam02`

Rulat cu `--post`, backend local și `--live-dir` în `SNAPSHOT_DIR`:

- 200 cadre, **3 evenimente** `RESTRICTED_ZONE`;
- 15,62 s end-to-end, ~12,8 FPS cu HTTP și scrierea live frame;
- rapoarte `source=template`;
- `/stream/stand12.mjpg` a servit exact cadrul scris de edge.

## Privacy

Auditul YuNet pe snapshot-urile generate:

| Clip | Snapshot-uri | Fețe la prag 0,6 | Fețe la prag 0,8 |
|---|---:|---:|---:|
| `broll_cam01` | 1 | 0 | 0 |
| `broll_cam02` | 5 | 0 | 0 |
| `broll_cam03` | 12 | 2 (0,67) | 0 |
| `broll_cam04` | 1 | 0 | 0 |
| `restricted-zone_cam01` | 1 | 0 | 0 |
| `restricted-zone_cam02` | 3 | 0 | 0 |
| `restricted-zone_cam02` live frame (full stack) | 1 | 1 (0,61) | 0 |

Cele două semnalări din `broll_cam03` și cea din live frame sunt pe zone deja blurate; verificarea vizuală a confirmat că fața este acoperită, iar la pragul 0,8 auditul iese curat. Nu s-a găsit nicio față neblurată în snapshot-urile salvate.

Auditul default (0,6) este intenționat conservator: poate semnala texturi din zonele blurate. Pentru un check rapid înainte de demo, `--threshold 0.8` a ieșit curat pe toate cele 6 clipuri; pentru o verificare de privacy, rulează implicit și inspectează hit-urile.

## Cifre pentru prezentare

Folosește cifre conservative și spune pe ce hardware au fost măsurate:

- **2 clipuri reale** `restricted-zone`, cu **2–3 evenimente** fiecare.
- **17,5 FPS wall / 21,0 processing** pe `cam01` (120 cadre), **20,0–28,9 FPS** pe clipurile `restricted-zone` rulate integral.
- **120 cadre RTSP în 9,34 s**, cu `--remote-config`.
- **200 cadre `cam02` prin backend în 15,62 s**, cu live frame real.
- **0 fețe neblurate** în snapshot-urile verificate; 2 semnalări slabe pe blur, clarificate manual.
- **38 teste ML + 90 teste backend**.

Nu folosi numărul de evenimente din B-roll ca „rată de falsuri” și nu promite PPE/FOD: detectorul implementat caută doar `person`, iar clipurile PPE/FOD lipsesc.

## Limite

- un singur poligon calibrat (`stand12`); `cam02` și B-roll nu au poligoane proprii;
- fără eșantion de 50–100 evenimente, deci fără rată de falsuri; cele 4 evenimente sunt în [`false-alarms.md`](false-alarms.md);
- soak-ul RTSP de 5 minute e făcut, dar doar edge-only și fără reconectare;
- fără PPE/FOD: nu există nici clipuri, nici cod de detecție;
- FPS-ul depinde de hardware-ul final; de remăsurat pe mașina de demo.

## Cum se reproduce

```bash
cd ml
uv run python -m safesight_ml.run \
  --source ../data/videos/<clip>.mp4 \
  --zones fixtures/zones.stand12.json \
  --camera-id stand12 --engine-on --dry-run \
  --out /tmp/clip-test/out \
  --metrics-json /tmp/clip-test/metrics.json

uv run python -m safesight_ml.privacy_audit --dir /tmp/clip-test/out/snapshots
```

Pentru full stack, adaugă `--post --api-url http://localhost:8000 --edge-token "$EDGE_TOKEN"` și `--live-dir ../backend/snapshots/live`.
