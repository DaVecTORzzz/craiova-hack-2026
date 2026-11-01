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

`fixtures/zones.stand12.json` are poligonul calibrat pe `cam01`: solul din fața motorului stâng până la roata din față (zona de pericol în care lucrează echipa de pushback). Camera din clip se mișcă, deci poligonul e aproximativ; pe o cameră fixă se trasează o dată pe cadrul de referință. Pe `cam01` dă 1 eveniment (track #3); marshaller-ul de lângă aripă și trecătorii nu mai declanșează. `--live-dir` scrie `live/stand12.jpg`, pe care backend-ul îl servește la `/stream/stand12.mjpg`. Cadrul live și snapshot-urile sunt blurate întâi, apoi adnotate: zona (roșu dacă e activă, gri dacă nu), caseta fiecărei persoane cu track și scor (roșu în zonă, verde în afara ei), eticheta `vesta` / `vesta ?` și o bară de stare. Cadrul live e scris atomic, la cel mult 1280 px lățime, pe un thread separat: detecția nu așteaptă blur-ul. YuNet pe cadrul complet rulează pe propriul thread, iar fiecare cadru live e ținut până termină o trecere YuNet pe un cadru *ulterior*; se blurează cu fețele din trecerea dinainte și din cea de după (cu margine de 50%), plus capul fiecărei persoane din cadrul curent. O față care apare între două treceri e prinsă de următoarea, deci live-ul merge cu sub o secundă în urmă; alertele nu așteaptă. Cadrele eliberate de o trecere sunt scrise eșalonat, cu distanța lor originală (cel mult `--live-fps`, implicit 30), nu aruncate. Blur-ul pe zonă se face micșorând zona de 8 ori, blurând-o și mărind-o la loc: același nivel de anonimizare ca `GaussianBlur(sigma=25)` (detaliu rămas 1,43 față de 1,50), de ~40× mai ieftin. Cu `--live-when-watched` (pornit de `dev.py demo`), cadrul live și trecerea YuNet rulează doar pentru camera deschisă în UI: backend-ul actualizează `live/<cameră>.watch` cât timp un client urmărește `/stream`; detecția și alertele rulează pe toate camerele. Snapshot-urile de incident și MP4-ul folosesc în continuare o trecere YuNet completă pe cadrul lor. Măsurat cu 3 camere pornite, una urmărită (31 octombrie 2026): clientul primește 13–16 cadre/s (înainte 5–7, inițial ~1), detecția urcă de la 10–12 la 16–20 cadre/s, iar prima imagine nouă după schimbarea camerei apare în ~0,8 s. `privacy_audit` pe toate cadrele live scrise în rulările de test: 0 fețe la 0,6 și 0,8. `metrics.json` are `live` (cadre aruncate pe motiv, `render_ms`, `face_pass_ms`). Cu `--realtime` (pornit de `dev.py demo` pe clipuri), un fișier e redat la FPS-ul lui, ca o cameră: fără el, pe GPU edge-ul trece de 30 fps, coada live se umple și aruncă majoritatea cadrelor. Măsurat pe `cam01` cu o cameră (31 octombrie 2026): 7,9 → 16,4 cadre live/s, pauza p95 dintre cadre 270 → 100 ms. Benchmark-urile rulează fără `--realtime`, cât de repede se poate.

Video adnotat, ca să vezi detecția cadru cu cadru (fișier local, nu intră în git):

```bash
uv run python -m safesight_ml --source ../data/videos/2026-10-30_restricted-zone_cam01_persoana-langa-motor.mp4 \
  --zones fixtures/zones.stand12.json --engine-on --dry-run --out out/cam01 --annotated-video out/cam01_annotated.mp4
```

Fiecare cadru e blurat și adnotat; la un eveniment apare 2 s un banner `ALERTA RESTRICTED_ZONE`. Randarea e mai lentă decât live-ul (~4 FPS pe 1080p, ~1 FPS pe 4K), pentru că blur-ul rulează pe fiecare cadru.

Vesta (`ppe.py`) e detectată după culoare (portocaliu / galben-verde fluorescent pe trunchi, inclusiv galben-verdele pal de pe vreme înnorată), fără model antrenat. Fiecare persoană are una din trei stări, iar starea `fără vestă` ridică `NO_PPE` într-o zonă `PPE_REQUIRED` care cere `hi_vis_vest`:

| Stare | Etichetă | Când |
|---|---|---|
| vestă | `vesta` | scorul netezit ≥ 0,10 |
| fără vestă | `FARA VESTA` (casetă portocalie dacă nu e și în zonă) | în ultimele 30 de cadre bune, 90% din scoruri < 0,03, persoana are ≥ 150 px și detecția e sigură (≥ 0,5) |
| nesigur | `vesta ?` | sub 5 cadre bune sau orice altceva |

Un cadru e „bun” doar dacă persoana are ≥ 80 px și caseta nu e tăiată de marginea cadrului. Regula pentru „fără vestă” e prudentă intenționat: pe clipurile noastre, scorurile mici veneau din casete parțiale, din obiecte luate drept persoane (barieră, echipament de bandă) și dintr-un marshaller mic, cu spatele, la care vesta se vede doar ca o fâșie la umeri, nu din oameni fără vestă. Măsurat pe 31 octombrie 2026: pe cele 6 clipuri, 0 cadre „fără vestă” (35 de persoane `vesta`, 16 `vesta ?`); pe imaginile etichetate, `vesta` (0,53) cu vestă și `FARA VESTA` (0,00) fără.

`no_vest` ridică `NO_PPE`, `unknown` nu ridică nimic — o persoană mică sau parțial ascunsă nu e raportată ca încălcare. Pe cele 6 clipuri, regula n-a produs niciun eveniment (886 cadre verificate pe `broll_cam03`), pentru că toți oamenii poartă vestă.

Asta **schimbă o decizie anterioară**: până acum vesta era doar afișată, iar `NO_PPE` se amâna până la un clip cu o încălcare reală. Acum evenimentul se emite din heuristică. Când modelul antrenat PPE ajunge în pipeline, starea `no_vest` se ia din detector, nu din culoare.

Ce `rule_type` produce ce eveniment:

| `rule_type` | Eveniment | Când |
|---|---|---|
| `RESTRICTED` | `RESTRICTED_ZONE` | oricine e în zonă, dacă zona e activă (`engine_on` sau `always`) |
| `PPE_REQUIRED` | `NO_PPE` | doar dacă un element din `required_ppe` e dovedit lipsă |
| `FOD_WATCH`, `NO_SMOKING`, `CROWD_WATCH` | — | nemapate: nu există detector, deci nu pot dovedi nimic |

`required_ppe` se verifică azi doar pentru `hi_vis_vest`. `hard_hat` și `ear_defenders` sunt în seed, dar nu au detector — o zonă care le cere nu ridică nimic pentru ele și nu le consideră niciodată îndeplinite. Persoana care poartă vestă într-o zonă PPE **nu** e evidențiată în overlay: caseta roșie înseamnă încălcare, nu prezență.

Integrare cu backend-ul:

```bash
uv run python -m safesight_ml.run \
  --source ../data/videos/2026-10-30_restricted-zone_cam01_persoana-langa-motor.mp4 \
  --zones fixtures/zones.stand12.json \
  --camera-id stand12 \
  --engine-on \
  --loop \
  --post \
  --live-dir ../backend/snapshots/live \
  --api-url http://localhost:8000 \
  --edge-token "$EDGE_TOKEN"
```

Cu `--loop`, clipul se reia la final, iar cadrul live se actualizează continuu. O trecere nouă emite evenimente doar dacă ultimul eveniment are cel puțin `--loop-cooldown-s` secunde (implicit 60). Pe `cam01` (9 s), asta înseamnă o alertă pe minut, nu una la 9 s. Fără limita asta, același incident ar ajunge în UI și pe Slack la fiecare trecere.

`--remote-config` ia zonele și `engine_on` din `GET /edge/zones` și le reîmprospătează la 30 s. Dacă backend-ul nu răspunde, folosește `fixtures/zones.stand12.json` și flag-ul `--engine-on`. Pentru `--remote-config`, zona din backend trebuie să aibă poligonul calibrat; altfel folosește `--zones`.

## Zone pe fiecare clip, cu camera în mișcare

Clipurile din `data/videos/` sunt filmate cu telefonul: camera se rotește, se înclină și face zoom (pe `cam01` ~19% din lățime, pe `broll_cam02` ~40% din înălțime). Un poligon fix ajunge pe alt asfalt după câteva secunde. Cu `--align-reference`, zona se desenează o dată pe primul cadru al clipului și apoi urmărește solul: la fiecare `--align-every` cadre (implicit 5), cadrul curent se potrivește cu cel de referință (ORB + RANSAC, doar OpenCV) și poligonul se mută odată cu imaginea. Dacă potrivirea eșuează, zona e „necunoscută”: nu se emite nimic, iar bara de stare arată `ZONA NEALINIATA`.

Fiecare clip are zona lui în `fixtures/zones/`, pe una dintre camerele din seed (contractul nu se schimbă). `id`-ul zonei este cel din seed pentru camera respectivă (`engine-left`, `taxiway-b`, `baggage-area`), pentru că `POST /edge/events` respinge cu 404 un `zone_id` necunoscut; diferă doar poligonul și `name`:

| Clip | Fișier | `camera_id` | Zona desenată |
|---|---|---|---|
| `restricted-zone_cam01` | `restricted-cam01.json` | `stand12` | motorul stâng până la roata din față (același poligon ca `zones.stand12.json`) |
| `restricted-zone_cam02` | `restricted-cam02.json` | `stand12` | bara de tractare și trenul din față |
| `broll_cam01` | `broll-cam01.json` | `taxiway-b` | sub vârful aripii |
| `broll_cam02` | `broll-cam02.json` | `baggage-area` | în fața prizei motorului drept |
| `broll_cam03` | `broll-cam03.json` | `stand12` | sub aripa stângă, lângă motor |
| `broll_cam04` | `broll-cam04.json` | `taxiway-b` | banda de rulare |

```bash
CLIP=../data/videos/2026-10-30_restricted-zone_cam02_lucratori-pushback-motor..mp4
uv run python -m safesight_ml.run --source "$CLIP" --align-reference "$CLIP" \
  --zones fixtures/zones/restricted-cam02.json --camera-id stand12 --engine-on --dry-run
```

Pentru RTSP, `--source` e fluxul, iar `--align-reference` rămâne clipul publicat (sau o imagine cu primul cadru).

Desenare și verificare zonă:

```bash
# click pe colțuri pe primul cadru, Enter afișează poligonul JSON (are nevoie de ecran)
uv run python -m safesight_ml.calibrate draw --source "$CLIP"
# zona aliniată pe 6 cadre din tot clipul, blurat, într-o singură imagine
uv run python -m safesight_ml.calibrate preview --source "$CLIP" \
  --zones fixtures/zones/restricted-cam02.json --out out/calib/cam02.jpg
```

Rezultat pe 31 octombrie 2026 (toate clipurile întregi, dry-run, `--engine-on`): alinierea nu s-a pierdut pe niciun clip și costă 5–17 ms la fiecare al 5-lea cadru. Pe `broll_cam02`, poligonul fix ajungea după zoom peste banda de bagaje și alerta pe șoferul ei (fals); cu aliniere, zona rămâne în fața motorului și alerta e pe persoana care intră acolo. Pe `restricted-cam02`, alinierea prinde în plus lucrătorul aplecat la bara de tractare. Pe celelalte clipuri evenimentele sunt aceleași. Poligoanele de B-roll sunt propuse de noi și trebuie validate de echipă pe preview.

## Clipuri 4K: `--max-size`

`--max-size N` micșorează cadrul imediat după citire, astfel încât latura cea mai lungă să fie cel mult `N` px. Detecția, blur-ul, snapshot-urile și live-ul folosesc cadrul micșorat. Pe 4K, costul e blur-ul (YuNet pe cadrul complet), nu detecția.

Se folosește doar unde s-a verificat că nu se pierd fețe. YuNet pe 40 de cadre din fiecare clip 4K (31 octombrie 2026):

| Clip | Fețe la 4K | la 1920 px | la 1280 px |
|---|---:|---:|---:|
| `broll_cam02` (`baggage-area` în demo) | 55 | 69 | 52 |
| `broll_cam03` | 143 | 71 | 5 |
| `restricted-zone_cam02` | 85 | 31 | 17 |

`dev.py demo` pornește `baggage-area` cu `--max-size 1920`; celelalte clipuri rămân la rezoluția lor. Cu 3 camere în paralel (RTX 3050), `baggage-area` trece de la 7,9 la 14,6 FPS, blur-ul de la 889 la 216 ms, snapshot-ul de la 2,4 MB la ~0,85 MB, cu aceleași evenimente; `privacy_audit` pe snapshot-uri și pe cadrul live: 0 fețe. Pentru alt clip 4K, repetă măsurarea înainte să-l micșorezi.

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

Pentru un soak de 5 minute, adaugă:

```bash
  --duration-s 300 --metrics-json out/soak.json
```

`--live-dir` trebuie să fie exact `SNAPSHOT_DIR/live` al backend-ului: implicit local `../backend/snapshots/live`, iar cu Docker `../backend/data/snapshots/live`. Dacă folosești alt `SNAPSHOT_DIR`, schimbă și aici, altfel `/stream` servește placeholder-ul.

Oprește serverul după demo:

```bash
podman rm -f safesight-rtsp 2>/dev/null || true
```

Verificat local pe 31 octombrie 2026: 120 de cadre citite din `rtsp://127.0.0.1:8554/stand12` în 9,34 s end-to-end, 2 evenimente `RESTRICTED_ZONE`, `--remote-config` activ, iar `/stream/stand12.mjpg` a servit exact cadrul scris de edge. Dacă backend-ul nu răspunde, edge-ul folosește `fixtures/zones.stand12.json` și `--engine-on`.

## Webcam laptop, verificare vestă live (experimental)

`--source webcam` (sau `webcam:N` pentru alt dispozitiv) citește camera locală prin OpenCV, cere 1280×720 și o tratează ca un flux live: se păstrează doar cadrul cel mai nou, fără `--realtime` și fără `--align-reference`. Blur-ul pe fețe rulează la fel ca pe clipuri.

```bash
python scripts/dev.py demo --webcam          # din rădăcina repo-ului
# sau doar edge-ul:
uv run python -m safesight_ml.run --source webcam --zones fixtures/zones/webcam-ppe.json \
  --camera-id baggage-area --zone-margin 0 --live-dir ../backend/snapshots/live --post
```

Webcam-ul folosește camera `baggage-area` din seed, deci contractul nu se schimbă. `fixtures/zones/webcam-ppe.json` face zona `PPE_REQUIRED` (`hi_vis_vest`) cât tot cadrul, iar `dev.py` o scrie în backend chiar dacă o rulare anterioară a pus acolo zona clipului. `--zone-margin 0` e necesar: picioarele sunt aproape de marginea de jos, iar cu marja de 10% persoana ar rămâne „în afara” zonei.

Heuristica vestei nu se schimbă, deci **încadrarea contează**: o casetă tăiată de marginea cadrului nu se judecă (`vesta ?`). Persoana trebuie să stea la 2–3 m, cu tot corpul în cadru. `FARA VESTA` apare după ≥ 10 cadre bune (≈ 1 s), cu persoana de ≥ 150 px și o detecție ≥ 0,5. Vesta trebuie să fie portocalie sau galben-verde fluorescentă. Netestat încă pe camera laptopului de prezentare.

## Soak și metrics

`--duration-s` oprește run-ul după timpul real, iar `--metrics-json` scrie un rezumat pentru benchmark și pentru triajul de falsuri:

```bash
uv run python -m safesight_ml.run --source rtsp://127.0.0.1:8554/stand12 \
  --camera-id stand12 --remote-config --post --duration-s 300 \
  --metrics-json out/soak.json --api-url http://localhost:8000 --edge-token "$EDGE_TOKEN"
```

Rezumatul conține `frames`, `events`, `event_types`, `event_details` (id, tip, zonă, track, confidence, timp), `elapsed_s` și `fps` end-to-end. `event_details` este lista pe care o poți eticheta manual pentru rata de falsuri.

`stages` dă timpul pe etape (`read`, `detect`, `blur`, `overlay`, `live_write` doar fără thread-ul live, `snapshot`, `emit`, `video_write`): `calls`, `total_s`, `mean_ms`. Aceeași linie apare la final în consolă (`stages: ...`). Pornește de aici înainte de orice optimizare: pe `cam01` cu `--live-dir`, `blur` (YuNet pe cadrul complet) costă de câteva ori mai mult decât `detect`, dar rulează doar de 2 ori pe secundă și la evenimente.

Pe o sursă RTSP/HTTP, un thread citește continuu fluxul și pipeline-ul ia mereu **cel mai nou cadru**; cadrele sărite apar în `dropped_frames`. Astfel alerta nu rămâne în urma fluxului când pipeline-ul e mai lent decât camera. Timpul din reguli (`now_s`) folosește numărul de cadre al sursei, nu pe cele procesate, deci debounce-ul rămâne în secunde reale. Pe fișiere nu se sare nimic: fiecare cadru e procesat, ca înainte.

**Fire pe mașină.** Fiecare edge crede că are toate nucleele: torch și OpenCV își pornesc câte un pool dimensionat după mașină, deci trei camere pun trei pool-uri pe aceleași nuclee. `--share-cpu N` (pus de `dev.py` când pornește mai multe camere) împarte nucleele **fizice** între ele, lăsând unul liber pentru API, JPEG și OS; `--threads N` forțează o valoare. Al doilea efect, mai mare decât împărțirea: libgomp își ține firele în așteptare activă între regiunile paralele, câte un nucleu fiecare. `run.py` setează `OMP_WAIT_POLICY=PASSIVE` înainte de orice import numeric, iar un edge la o cameră scade de la 7,4 la 0,9 nuclee cu aceeași muncă. Măsurat pe laptop, 1 nov 2026: 3 camere, camera urmărită 0,9 → 14,6 cadre/s, CPU total al edge-urilor 1407% → 775% din 1600%; cu o cameră, 21,5 → 21,4 (neschimbat). Peste 8 fire per edge (`--threads 15`) coboară la 16,8 cadre/s: mai multe fire decât nuclee fizice încetinesc, nu ajută.

## Verificare privacy pe snapshot-uri

După o sesiune reală, verifică snapshot-urile salvate cu același YuNet folosit la blur:

```bash
uv run python -m safesight_ml.privacy_audit --dir ../backend/snapshots
uv run python -m safesight_ml.privacy_audit --dir ../backend/snapshots --json
# cu Docker: --dir ../backend/data/snapshots
```

Exit code: `0` curat, `1` fețe detectate, `2` director/model lipsă, niciun snapshot sau imagine necitibilă. Tool-ul scanează recursiv `.jpg`, `.jpeg` și `.png`; nu blurează nimic, doar semnalează ce a scăpat. Pentru un singur fișier, dă calea direct la `--dir`.

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
  privacy_audit.py  # scanare snapshot-uri pentru fețe neblurate
  sink.py      # JsonlSink (dry-run) și HttpSink (/edge/snapshots, /edge/events)
  live.py      # ultimul cadru blurat + adnotat pentru /stream MJPEG; video MP4 adnotat
  overlay.py   # desenează zone, casete, vestă, stare și banner de alertă peste cadrul deja blurat
  ppe.py       # stare vestă după culoare (vest / no_vest / unknown); no_vest ridică NO_PPE
  pipeline.py  # cadru -> detecții -> reguli -> eveniment
  remote.py    # GET /edge/zones (zone + engine_on)
  align.py     # zona urmărește camera care se mișcă (ORB + omografie față de cadrul de referință)
  calibrate.py # desenare poligon și preview cu zona aliniată
  capture.py   # pe RTSP/HTTP, mereu cel mai nou cadru
  run.py       # CLI
fixtures/
  zones.json          # zona engine-left din contract
  zones.stand12.json  # poligon calibrat pe clipul real
  zones/              # o zonă per clip, desenată pe primul cadru
```

## Reguli

- Punctul de intrare în zonă este **centrul de jos al bbox-ului** (picioarele), nu centrul cutiei.
- Marginea zonei are toleranță (`--zone-margin`, implicit 0,10): persoana intră când picioarele sunt cu 10% din înălțimea ei în interiorul poligonului și iese când sunt cu 10% în afară; între ele, starea rămâne. Cine stă pe linie nu mai intră și iese de la un cadru la altul. Distanța e măsurată în înălțimi de cadru, cu aspectul imaginii, deci toleranța e aceeași pe orizontală și pe verticală. `--zone-margin 0` = testul vechi cu un singur punct.
- O casetă care atinge marginea de jos a cadrului nu arată picioarele: starea rămâne cea anterioară și nu începe o intrare nouă.
- `zone_transitions` în metrics numără intrările și ieșirile; pe cele 6 clipuri, cu aliniere, toleranța le scade de la 25 la 19, cu aceleași evenimente.
- `active_when=engine_on` nu emite nimic când motorul e oprit; `--remote-config` ia starea din backend.
- `debounce_s` și confidence temporal: minim 5 cadre observate și 80% confirmare.
- `detected_at` folosește ceasul real al procesării, nu timpul video; `now_s` rămâne pentru durata în zonă.
- `snapshot_url` e HTTP; niciodată `minio://`. Snapshot-ul se urcă cu `event_id` ca form field.
- `FaceBlurrer` blurează fețele YuNet **și** partea de sus a fiecărui bbox de persoană, ca plasă de siguranță pentru fețe mici.
- Stările track-urilor dispărute se curăță după cooldown.
- `status`, `report`, `received_at`, `notified_at`, `escalated_at`, `acked_at`, `acked_by` nu se trimit din edge.
- Modelul de fețe lipsește → `FaceBlurrer` fail-closed; nu se salvează imagine neblurată.
- `--fake` folosește `NoopBlurrer` doar pentru cadre sintetice, fără fețe.
- YuNet rulează pe cadrul la rezoluție completă. Micșorarea înainte de blur pierde fețe (pe `cam01`, 15 → 7 fețe la 1280 px; pe `cam02` 4K, 40 → 7), deci nu se folosește ca optimizare.
- YuNet rulează prin **ONNX Runtime**, nu prin `cv2.FaceDetectorYN`: același model, aceeași matematică de decodare (`sqrt(cls*obj)`, NMS 0,3), aceleași fețe. Măsurat pe cele trei clipuri din demo, 40 de cadre fiecare (1 nov 2026): 42,1 → 26,4 ms pe `cam01`, 18,6 → 10,7 ms pe `broll_cam01`, 45,0 → 26,3 ms pe `broll_cam02`, cu număr de fețe identic și 100% potrivire la IoU 0,5. Live pe o cameră: 15,4 → 21,5 cadre/s. Modelul publicat are intrare fixă 640×640, deci `privacy.py` o face dinamică la încărcare și umple cadrul până la multiplu de 32 pe ambele laturi (rândurile și coloanele de umplutură sunt goale, deci coordonatele nu se rescalează). Firele se schimbă cu `SAFESIGHT_FACE_THREADS` (implicit 4; 1/2/3/4/6 fire dau 53/35/29/26/25 ms). Modelul `int8bq` din opencv_zoo **nu** poate rula în ONNX Runtime (block quantization nesuportată), deci implicit rămâne `face_detection_yunet_2023mar.onnx`. Pe o mașină cu placă video, sesiunea trece automat pe `CUDAExecutionProvider` sau `ROCMExecutionProvider` (fallback pe CPU); iGPU-urile rămân pe CPU intenționat, unde transferul costă mai mult decât economisește la un model atât de mic.

## Ce nu intră încă

- PPE (vestă, cască, antifoane) și fine-tuning;
- FOD pe cadru de referință;
- VLM pentru fum;
- buffer/retry la pană de conexiune;
- rata de falsuri alarme, măsurată pe 50–100 evenimente;
- reconectare automată la căderea fluxului RTSP (acum procesul se oprește la primul `read()` eșuat).

Verificare: `uv run pytest` și `uv run python -m safesight_ml.run --fake --engine-on --dry-run`. Cifrele reale sunt în [`docs/benchmark.md`](docs/benchmark.md), testarea pe toate clipurile în [`docs/clip-tests.md`](docs/clip-tests.md), soak-ul în [`docs/soak.md`](docs/soak.md), iar eșantionul de falsuri în [`docs/false-alarms.md`](docs/false-alarms.md).
