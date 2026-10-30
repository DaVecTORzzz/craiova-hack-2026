# SafeTarmac AI

Inspector automat de siguranță pentru platforma aeroportului. Camerele existente sunt analizate local, pe un Edge Box: echipament de protecție lipsă, persoane în zone restricționate, obiecte pe pistă (FOD), fumat. Fiecare încălcare pornește singură fluxul de răspuns: alertă cu poză, raport de incident scris de AI și escaladare dacă nimeni nu confirmă.

Video-ul nu iese din aeroport. Fețele sunt blurate înainte de orice salvare.

## Structura

| Folder | Ce conține | Responsabil |
|---|---|---|
| `ml/` | Detecție (YOLO26), tracking, zone, FOD, blur pe fețe | Andrei |
| `backend/` | FastAPI, rule engine, WebSocket, stream video, stocare | Max |
| `automation/` | Raport AI, notificări Slack, escaladare, raport de tură | Dalina |
| `frontend/` | Dashboard React + Vite și PWA pentru telefon | Ariana |
| `demo/` | Scenariul demo și instrucțiunile pentru înregistrarea de rezervă | Ariana + Dalina |
| `docs/` | Contractul API și alte documente comune | toți |

Contractul dintre module e în [`docs/contract.md`](docs/contract.md). Se schimbă doar prin pull request aprobat de cel afectat.

## Pornire

1. `cp .env.example .env` și completează cheile.
2. Fiecare modul are în folderul lui un `README.md` cu pornirea și comanda de verificare.
3. Cât timp un modul nu e gata, ceilalți lucrează cu `USE_MOCK=true` și cu fixture-urile din `frontend/fixtures/`.

## Date care nu intră în git

Video-urile de test (`.mp4`), modelele antrenate (`.pt`, `.onnx`) și baza de date locală sunt ignorate de git. Le țineți în folderul comun din Google Drive: `[link Drive]`.

## Reguli de lucru

- `main` trebuie să ruleze mereu. Lucrați pe branch-uri scurte (`max/rule-engine`, `ariana/live-monitor`) și intrați în `main` prin pull request.
- Fiecare lucrează în folderul lui. Pentru o schimbare în folderul altcuiva, deschideți un issue sau îi scrieți.
- Commit-uri cu prefix: `ml:`, `api:`, `ui:`, `auto:`, `docs:`.
- Asistenții AI (Claude Code etc.) citesc regulile din [`CLAUDE.md`](CLAUDE.md).
