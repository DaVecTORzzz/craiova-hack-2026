# frontend/ — dashboard și PWA

Responsabilă: **Ariana**

- Brief-ul complet: rolul C (Live, Incidente, Zone, Rapoarte, alerte mobile).
- Ecranele: canvas-ul de wireframe-uri SafeTarmac AI.
- Pornește cu fixture-urile din `fixtures/`, cu aceeași structură ca evenimentele reale (`docs/contract.md`). Trecerea pe API nu trebuie să schimbe componentele.
- Folosește `snapshot_url` direct în `<img src>`; nu construi `minio://`.
- `confidence` este obiect: afișează „0.91 · 14/15 cadre”, formatat din `{detector, temporal}`.
- Severitate doar `CRITICAL` / `WARNING`; `RESOLVED` este status, nu severitate.
- Dacă WebSocket-ul cade: banner „Conexiune pierdută” și polling la 2 secunde pe `GET /events`.

Verificare: `npm run build` trece, iar pagina Live afișează evenimentele din fixture-uri.
