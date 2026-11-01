# Run sheet — SafeSight, 90 de secunde

Scop: mentorii înțeleg problema, văd incidente reale pe mai multe camere în UI și pleacă cu limitele clare.

## T-10 minute: preflight

```bash
./run.sh doctor
```

- închide alte procese pe `:8000` și `:5173` (sau folosește `--backend-port` / `--frontend-port`);
- închide orice antrenare sau proces greu pe GPU: demo-ul rulează 3 edge-uri în paralel;
- opțional, pentru demo curat (fără incidentele din repetiții):

```bash
rm -f backend/safesight.db
rm -rf backend/snapshots
```

- pornește stack-ul:

```bash
./run.sh demo
```

Pornește backend-ul, frontend-ul și câte un edge pe fiecare cameră, fiecare pe clipul lui, în buclă:

| Cameră | Clip | Ce arată |
|---|---|---|
| CAM-01 Stand 12 | persoană lângă motor | intrare în zona motorului (`RESTRICTED_ZONE`, CRITICAL) |
| CAM-02 Taxiway B | marshaller cu conuri | feed live; regula zonei e `FOD_WATCH`, iar FOD nu are detector — fără incidente |
| CAM-03 Baggage area | avion la poarta de bagaje (4K, citit la 1920 px) | feed live; regula e `PPE_REQUIRED` — incident doar dacă cineva nu are vestă, iar în clip toți au |

- deschide `http://localhost:5173`;
- lasă 60–90 s: CAM-01 dă primul incident în primul minut, apoi cel mult unul pe minut; CAM-02 și CAM-03 arată feed-ul adnotat, dar pe aceste clipuri nu au ce raporta;
- verifică în terminal liniile `Edge: <cameră> <- <clip>` pentru toate trei; un mesaj `edge <cameră> s-a oprit` înseamnă că acea cameră a rămas pe ultimul cadru;
- dacă nu apare niciun incident după 90 s:

```bash
python scripts/dev.py fallback
```

- dacă Slack nu e configurat (`SLACK_WEBHOOK_URL` în `.env`), spune din start: „notificarea Slack e simulată în acest mediu”.

## T-0: 90 de secunde

| Timp | Ce faci | Ce spui |
|---|---|---|
| 0–10 s | Live, CAM-01 | „Camerele existente devin un flux de siguranță, nu doar înregistrare.” |
| 10–25 s | Feed-ul adnotat: zonă roșie, persoane cu track, etichetă `vesta` | „Persoana intră în zona motorului; e urmărită de la un cadru la altul, iar zona rămâne pe asfalt chiar dacă camera se mișcă.” |
| 25–35 s | Meniul **Cameră** → CAM-03, apoi CAM-02 | „Aceeași procesare pe fiecare cameră, în paralel: detecție, tracking, blur. Incidentul apare doar unde regula zonei poate fi evaluată — aici FOD și PPE n-au detector, deci camerele astea tac.” |
| 35–50 s | Click pe un card CRITICAL → **Incidente & XAI**; snapshot, cronologie, raport | „Alerta are dovadă blurată, severitate, timp și un raport de incident.” |
| 50–58 s | Click **Acknowledge (Confirmă)** | „Operatorul confirmă; escaladarea se oprește. Human-in-the-loop.” |
| 58–66 s | Arată mesajul Slack | „Slack primește text + link, fără imagini și fără butoane.” |
| 66–78 s | Click **Rapoarte Tură** | „KPI pe tură, distribuție pe tipuri, rezumat. Fals pozitivele nu intră în total — se numără separat. Acoperirea arată minutele în care o cameră a fost oarbă.” |
| 78–85 s | Click **Edge & Audit** | „Totul rulează la margine: detecție, tracking, blur și decizia. Backend-ul primește doar evenimentul, nu video.” |
| 85–90 s | Închide cu privacy | „Video-ul brut nu iese din aeroport; fețele sunt blurate la edge înainte de orice salvare.” |

### Opțional: fluxul `NO_PPE` (simulat)

În clipuri toți poartă vestă, deci un `NO_PPE` real nu apare live. Pentru a arăta fluxul (incident WARNING, raport, Slack, ack):

```bash
python scripts/dev.py fallback --type NO_PPE
# sau cu un JPEG deja blurat:
python scripts/dev.py fallback --type NO_PPE --snapshot <jpeg-blurat>
```

Spune explicit: „evenimentul e trimis manual pe aceleași rute ca edge-ul; detecția de vestă live e afișată pe persoane, dar alerta `NO_PPE` nu e încă activă”.

### Opțional: camera moartă devine incident (90 s)

Fiecare edge trimite heartbeat prin poll-ul de configurație (la 30 s). Oprește unul:

```bash
# în terminalul run.sh: Ctrl-C pe linia „edge <camera>” (sau închide laptopul de demo pe acea cameră)
```

- după `CAMERA_OFFLINE_AFTER_S` (implicit 90 s) apare un singur `CAMERA_OFFLINE` (WARNING), cu snapshot placeholder și fără escaladare
- repornește edge-ul: primul heartbeat rezolvă incidentul (`status: resolved`, acțiune „recovered”) și închide fereastra de orbire din raport
- în **Rapoarte Tură**, „Acoperire camere” scade cu minutele cât a fost oarbă

Spune: „camera care tace nu mai e o gaură în pază: devine incident, iar revenirea îl închide singură.”

## Dacă ceva pică

- **Nu apare incident:** `python scripts/dev.py fallback`; evenimentul apare în UI.
- **O cameră îngheață:** alege alta din meniul **Cameră**; terminalul arată ce edge s-a oprit.
- **Laptopul nu ține 3 camere:** repornește cu `python scripts/dev.py demo --cameras stand12`.
- **Feed-ul live nu merge:** sari la incident + raport + rapoarte; spune că feed-ul e plan B.
- **Slack nu răspunde:** arată log-ul „notification simulated”; nu pretinde că a plecat.
- **Raportul e template:** spune „source=template; LLM-ul e opțional”.

## Ce nu spui

- „`NO_PPE` / FOD merg live” — nu merg. Vesta e doar etichetată pe persoane (după culoare), fără alertă.
- „Model PPE antrenat” — dataset-ul există, antrenarea nu e terminată.
- „0% falsuri” — avem un eșantion mic, verificat vizual; rata de falsuri nu e măsurată.
- „Trei incidente, câte unul pe cameră” — doar CAM-01 produce. CAM-02 și CAM-03 arată feed-ul adnotat, dar regula lor (`FOD_WATCH`, `PPE_REQUIRED`) nu poate fi evaluată fără detector.
- „Camere live din aeroport” — clipurile sunt reale (stock), redate ca flux live.
- „Camera offline e prinsă instant” — pragul e 90 s (3 heartbeats ratate); sub asta ar fi zgomot la fiecare microîntrerupere.
- „Alertele ajung garantat în Slack” — coada garantează că nu se pierd la timeout sau restart; dacă Slack e jos mai mult de ~2 minute, rândul rămâne `failed` și se vede în `/health`.
- „Producție gata” — auth, audit, retenție și camere reale sunt roadmap.

## Întrebări probabile

**Ce e real?**
YOLO26 + ByteTrack, zonele care urmăresc camera, eticheta de vestă după culoare, blurul, backend-ul, UI-ul, ack-ul, escaladarea, raportul, watchdog-ul de cameră, coada de notificări cu retry, testele.

**Ce e stock sau simulat?**
Clipurile (stock, filmate din mână, redate în buclă ca 3 camere), operatorul, `NO_PPE` (trimis prin fallback), Slack dacă nu e webhook, raportul dacă nu e cheie Groq.

**De ce se mișcă zona în video?**
Clipurile sunt filmate cu telefonul. Zona e desenată pe primul cadru și urmărește solul (potrivire de puncte + omografie). Pe o cameră fixă de aeroport nu ar fi nevoie.

**Cum știți dacă are vestă?**
Azi, după culoarea fluorescentă pe trunchi, cu trei stări: `vesta`, `FARA VESTA`, `vesta ?`. „Fără vestă” se afirmă doar pe persoane mari în cadru și detectate sigur; pe cele 6 clipuri, 0 cadre marcate greșit. Următorul pas e modelul PPE antrenat pe ~25.000 de imagini.

**Cât de rapid?**
Cu 3 camere în paralel, pe un laptop cu RTX 3050: 19,5 / 29,7 / 14,6 FPS (CAM-01 / CAM-02 / CAM-03). Remăsoară pe laptopul de demo.

**Cât de stabil e?**
5 minute RTSP pe o cameră: 8.697 cadre, 28,99 FPS, 0 căderi.

**Ce urmează?**
O cameră reală pentru pilot, modelul PPE antrenat și alerta `NO_PPE`, clipuri FOD, auth.

## După demo

```bash
# Ctrl-C în terminalul run.sh
rm -f backend/safesight.db
rm -rf backend/snapshots
```
