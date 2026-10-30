# automation/ — raport AI, notificări, escaladare, raport de tură

Responsabil: **Dalina**

- `on_event_created(event)` pornește un task asincron pentru fiecare eveniment nou; backend-ul îl apelează în proces, nu prin `PATCH /events/{id}`.
- Raport de incident: Groq `llama-3.3-70b-versatile`, mod JSON, temperatură 0,2. Acțiunea recomandată vine dintr-un tabel fix pe tip; LLM-ul doar reformulează. Dacă API-ul pică, raport-șablon din metadate, cu `source=template`.
- Notificări: Slack incoming webhook, text + link la incident, fără imagini și fără butoane. Confirmarea se face în aplicație, ca să rămână în `event_actions`. Codul e un adaptor (`Notifier.send(event)`), ca alt canal să se adauge ușor.
- Escaladare după `escalate_after_s` al zonei; `null` = fără escaladare. Seed demo 30 s, producție 120 s. `DEFAULT_ESCALATE_AFTER_S` este doar fallback.
- Raport de tură: cifrele le calculează backend-ul; LLM-ul scrie doar rezumatul de 2–3 fraze, din cifrele primite.
- VLM pentru fum (Claude Haiku) este stretch și nu intră în demo.

Verificare: `python -m automation.smoke` trimite o alertă de test pe Slack, iar `python -m automation.report` generează un raport dintr-un fixture.
