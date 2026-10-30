# automation/ — raport AI, notificări, escaladare, raport de tură

Responsabil: **Dalina**

- `on_event_created(event)` pornește un task asincron pentru fiecare eveniment nou.
- Raport de incident: LLM pe Groq (verificați modelul curent în consolă), răspuns JSON; dacă API-ul pică, raport-șablon din metadate.
- Notificări: Slack, cu butoane Acknowledge / False positive. Codul e un adaptor (`Notifier.send(event)`), ca alt canal să se adauge ușor.
- Escaladare după `ESCALATE_AFTER_S` dacă alerta e încă `open`.
- Raport de tură: agregare + rezumat LLM de 2–3 fraze.

Verificare: `python -m automation.smoke` trimite o alertă de test pe Slack.
