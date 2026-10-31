# Run SafeSight on Linux, macOS or Windows

Un singur script cross-platform, cu Python 3.12+. Nu are nevoie de bash, make sau Docker.

## Cerințe

| Unealtă | De ce | Instalare |
|---|---|---|
| Python 3.12+ | rulează scriptul, backend-ul și ML-ul | [python.org](https://www.python.org/downloads/) |
| `uv` | instalează și rulează backend-ul + ML | `curl -LsSf https://astral.sh/uv/install.sh \| sh` (macOS/Linux) sau PowerShell de pe [astral.sh/uv](https://astral.sh/uv) |
| Node.js 18+ + npm | frontend Vite | [nodejs.org](https://nodejs.org/) sau `winget install OpenJS.NodeJS.LTS` |
| `ffmpeg` | opțional, doar pentru RTSP | `brew install ffmpeg`, `apt install ffmpeg`, `winget install Gyan.FFmpeg` |

Verificare rapidă:

```bash
python scripts/dev.py doctor
```

## Setup, o singură dată

```bash
python scripts/dev.py setup
```

Instalează dependențele backend, ML (`ultralytics` inclus) și frontend, apoi descarcă modelul YuNet pentru blur. Dacă vrei un setup mai rapid, fără detecție reală:

```bash
python scripts/dev.py setup --skip-yolo
```

## Demo complet

```bash
python scripts/dev.py demo
```

Pornește:

- backend-ul pe `http://localhost:8000`;
- frontend-ul pe `http://localhost:5173`;
- edge-ul pe clipul implicit din `data/videos/`, scrie evenimente în backend și live frame pentru `/stream`.

Ctrl-C oprește tot. Dacă backend-ul nu e gata, scriptul așteaptă `/health` înainte de edge.

Variante:

```bash
python scripts/dev.py demo --no-ml          # doar backend + frontend
python scripts/dev.py demo --mock           # backend mock, fără model
python scripts/dev.py demo --clip data/videos/<clip>.mp4
python scripts/dev.py demo --rtsp rtsp://127.0.0.1:8554/stand12
```

`--clip` și `--rtsp` se exclud. Clipul se procesează o dată, apoi edge-ul se oprește; fluxul RTSP rulează până la Ctrl-C. Pentru un RTSP local din clip, vezi `ml/README.md` (mediamtx + `ml/scripts/rtsp-loop.sh`). Credențialele din URL-ul RTSP nu apar în terminal (`rtsp://***@host/...`).

## Fallback demo

Dacă edge-ul, clipul sau modelul pică, backend-ul poate primi un eveniment demo prin aceleași rute edge. Backend-ul trebuie să ruleze deja.

```bash
python scripts/dev.py fallback
python scripts/dev.py fallback --type FOD --no-engine
python scripts/dev.py fallback --type NO_PPE
python scripts/dev.py fallback --snapshot /path/to/already-blurred.jpg
```

`--snapshot` trebuie să fie un JPEG **deja blurat**. Nu folosi cadrele din `data/reference_frames/` — acelea conțin fețe neblurate. Scriptul folosește tokenul din `.env`/mediu și API-ul de pe `localhost:8000`; `--api-url` și `--backend-port` sunt disponibile pentru alt port.

## Pornire pe bucăți

```bash
python scripts/dev.py backend               # doar API
python scripts/dev.py frontend              # doar UI
python scripts/dev.py all                   # backend + frontend
python scripts/dev.py ml -- --source ../data/videos/<clip>.mp4 --zones fixtures/zones.stand12.json
```

`ml` forwardează argumentele după `--` către `safesight_ml.run`. Pentru RTSP, vezi `ml/README.md`.

## Verificare

```bash
python scripts/dev.py check
```

Rulează testele backend (**90**), testele ML (**38**), smoke-ul `automation` și build-ul frontend.

## Windows

Din `cmd.exe`:

```bat
py -3 scripts\dev.py setup
py -3 scripts\dev.py demo
```

sau, dacă `python`/`py` e în PATH:

```bat
run.cmd demo
```

## macOS / Linux

```bash
./run.sh setup
./run.sh demo
```

sau direct `python3 scripts/dev.py ...`.

## Porturi și mediu

```bash
python scripts/dev.py all --backend-port 8000 --frontend-port 5173
```

`.env` la rădăcină este opțional; backend-ul are default-uri sigure. Pentru Slack, Groq sau alte chei:

```bash
cp .env.example .env
# editează .env
```

Scriptul forțează `USE_MOCK=false` pe `all`/`demo`; `--mock` pornește doar backend-ul cu evenimente false. UI-ul rămâne mereu pe API-ul real (`VITE_USE_MOCK=false`), ca evenimentele mock și ack-urile să treacă prin backend.

Launcher-ul citește `EDGE_TOKEN` și `SNAPSHOT_DIR` din `.env` (sau din mediu); restul cheilor rămân pentru backend. Dacă `SNAPSHOT_DIR` e relativ, calea se rezolvă față de `backend/`, iar live frame-ul se scrie în `SNAPSHOT_DIR/live`. `--edge-token` are prioritate față de `.env`.

## Dacă ceva nu merge

- `uv: command not found` → instalează `uv` și redeschide terminalul.
- `npm: command not found` → instalează Node.js LTS.
- `address already in use` → schimbă portul cu `--backend-port` / `--frontend-port`.
- `model lipsește` → rulează `python scripts/dev.py setup`.
- `clipul lipsește` → pune clipul în `data/videos/` sau folosește `backend/scripts/demo_event.py` ca fallback.
- Windows: dacă `py -3` nu e disponibil, folosește `python scripts\dev.py ...`.
