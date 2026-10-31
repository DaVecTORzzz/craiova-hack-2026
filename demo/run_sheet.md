# Run sheet — SafeSight, 90 de secunde

Scop: mentorii înțeleg problema, văd un incident real în UI și pleacă cu limitele clare.

## T-10 minute: preflight

```bash
./run.sh doctor
```

- închide alte procese pe `:8000` și `:5173`;
- opțional, pentru demo curat:

```bash
rm -f backend/safesight.db
rm -rf backend/snapshots
```

- pornește stack-ul:

```bash
./run.sh demo
```

- deschide `http://localhost:5173`;
- lasă 30–60 s să apară primul eveniment;
- verifică în terminal că backend-ul e `online` și edge-ul e `ACTIV`;
- dacă nu apare niciun incident după 15 s:

```bash
python scripts/dev.py fallback
```

- dacă Slack nu e configurat, spune din start: „notificarea Slack e simulată în acest mediu”.

## T-0: 90 de secunde

| Timp | Ce faci | Ce spui |
|---|---|---|
| 0–10 s | Arată Live-ul cu CAM-01 | „Camerele existente devin un flux de siguranță, nu doar înregistrare.” |
| 10–25 s | Arată feed-ul adnotat: zonă roșie, persoane, track | „Persoana intră în zona motorului; detectorul o urmărește, nu doar o vede într-un cadru.” |
| 25–40 s | Click pe cardul CRITICAL → **Incidente & XAI**; arată snapshot, cronologie, raport | „Alerta are dovadă, severitate, timp și un raport de incident.” |
| 40–50 s | Click **Acknowledge (Confirmă)** | „Operatorul confirmă; escaladarea se oprește. Human-in-the-loop.” |
| 50–60 s | Arată textul Slack / log-ul de notificare | „Slack primește text + link, fără imagini și fără butoane.” |
| 60–75 s | Click **Rapoarte Tură** | „KPI pe tură, distribuție pe tipuri, rezumat.” |
| 75–85 s | Click **Alerte Mobile PWA** | „Aceeași alertă ajunge pe telefon; butoane mari pentru operator.” |
| 85–90 s | Închide cu privacy | „Video-ul brut nu iese din aeroport; snapshot-urile sunt blurate la edge.” |

## Dacă ceva pică

- **Nu apare incident:** `python scripts/dev.py fallback`; evenimentul apare în UI.
- **Feed-ul live nu merge:** sari la incident + raport + rapoarte; spune că feed-ul e plan B.
- **Slack nu răspunde:** arată log-ul „notification simulated”; nu pretinde că a plecat.
- **Raportul e template:** spune „source=template; LLM-ul e opțional”.
- **Cineva apasă CAM-02/03:** explică „demo-ul rulează un singur edge; celelalte camere nu au feed live în acest setup”.

## Ce nu spui

- „PPE/FOD merg live” — nu merg.
- „0% falsuri” — avem 4 TP / 0 FP pe un eșantion mic.
- „Camera live din aeroport” — clipul e real, dar redat ca flux live.
- „Multi-camera live” — un singur edge în demo.
- „Producție gata” — auth, audit, retenție și multi-camera sunt roadmap.

## Întrebări probabile

**Ce e real?**
YOLO26 + ByteTrack, zonele, blurul, backend-ul, UI-ul, ack-ul, raportul, testele.

**Ce e simulat?**
Clipul redat în buclă, operatorul, Slack dacă nu e webhook, raportul dacă nu e cheie Groq.

**De ce video, nu poze?**
Pozele antrenează modelul. Video-ul testează tracking-ul, intrarea în zonă, debounce-ul și evenimentul în timp.

**Cât de stabil e?**
5 minute RTSP: 8.697 cadre, 28,99 FPS, 0 căderi.

**Cât de rapid?**
17,5 FPS wall / 21,0 processing pe laptopul de benchmark.

**Ce urmează?**
O cameră reală pentru pilot, clipuri PPE/FOD, antrenare separată, auth și multi-camera.

## După demo

```bash
# Ctrl-C în terminalul run.sh
rm -f backend/safesight.db
rm -rf backend/snapshots
```
