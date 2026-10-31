# SafeSight command center — frontend

Responsabilă: **Ariana**

Brief intern: `safesight-docs/03_C_frontend.typ` (repo privat). Contractul canonic: `docs/contract.md`.

## Pornire

```bash
cd frontend
npm ci
cp .env.example .env
npm run dev
```

`.env`:

```env
VITE_API_URL=http://localhost:8000
VITE_USE_MOCK=false
```

Backend-ul trebuie pornit pe `:8000`; CORS-ul implicit acceptă `http://localhost:5173`.

## Ce e conectat

- `src/services/api.js` → API-ul real: camere, evenimente, zone, KPI, raport de tură, acțiuni, snapshots.
- `snapshot_url` relativ este prefixat cu `VITE_API_URL`, ca `<img>` să funcționeze din alt origin.
- Live folosește `GET /stream/{camera}.mjpg`; dacă stream-ul pică, arată fallback-ul local.
- WebSocket `/ws/events` primește `event.created` / `event.updated`; dacă pică, polling la 2 s.
- Zonele trimit `rule_type`, `polygon` normalizat și `notify_channel: slack` conform contractului.
- Acțiunile operator trimit `operator` și folosesc răspunsul backend-ului.

`VITE_USE_MOCK=true` rămâne doar pentru dezvoltare fără backend. Datele mock sunt legacy și nu trebuie folosite în demo.

## Fișiere legacy

`App.jsx` din rădăcină și `standalone-preview.html` nu sunt încărcate de `index.html`; entry point-ul este `src/main.jsx`. Nu le folosi pentru demo.

## Verificare

```bash
npm run build
```

Build-ul trebuie să treacă. Pentru integrare, rulează backend-ul și verifică în browser: Live primește evenimente, ack schimbă statusul, Zone salvează, Rapoarte încarcă tura.
