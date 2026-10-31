"""Raport AI pentru SafeTarmac — generează textele, nu trimite nimic.

Backend-ul deține ingestia, escaladarea și trimiterea efectivă către Slack.
Acțiunea recomandată vine din tabelul fix pe tip; LLM-ul doar reformulează.
Dacă LLM-ul lipsește sau pică, se folosește fallback-ul pe reguli.
"""

import json
import os
import urllib.request
from datetime import datetime, timezone

# Tabelul fix pe tip de eveniment: acțiunea recomandată NU vine de la LLM.
RULES = {
    "restricted_zone": {
        "severity": "ridicata",
        "what": "Persoana in zona restrictionata (motor)",
        "severity_reason": "Risc de accidentare grava langa motorul in functiune.",
        "recommended_action": "Indepartati imediat persoana din zona si opriti operatiunile pana la confirmare.",
    },
    "no_ppe": {
        "severity": "medie",
        "what": "Echipier fara echipament de protectie complet",
        "severity_reason": "Lipsa vestei sau a castii creste riscul de accidentare pe apron.",
        "recommended_action": "Notificati coordonatorul; echipierul isi completeaza echipamentul inainte de reluarea lucrului.",
    },
    "fod": {
        "severity": "ridicata",
        "what": "Obiect strain (FOD) detectat pe suprafata de miscare",
        "severity_reason": "Obiectele pe asfalt pot fi aspirate de motor sau pot avaria aeronava.",
        "recommended_action": "Suspendati operatiunile pe taxiway, indeparcati si inspectati obiectul.",
    },
}

_DEFAULT = {
    "severity": "medie",
    "what": "Eveniment de siguranta nespecificat",
    "severity_reason": "Tip de eveniment necunoscut; necesita verificare umana.",
    "recommended_action": "Un operator uman verifica imaginile si decide actiunea.",
}

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def _rephrase_with_llm(report: dict) -> dict | None:
    """LLM-ul doar reformulează textele; întoarce None dacă lipsește/pică."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
    payload = {
        "model": model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "Reformulezi texte de siguranță în română, clar și scurt. "
                    "Răspunzi DOAR cu JSON valid cu cheile: what, severity_reason, "
                    "recommended_action. Nu schimbi sensul și nu adaugi fapte."
                ),
            },
            {"role": "user", "content": json.dumps(report, ensure_ascii=False)},
        ],
    }
    req = urllib.request.Request(
        GROQ_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        rephrased = json.loads(content)
        if not all(k in rephrased for k in ("what", "severity_reason", "recommended_action")):
            return None
        return rephrased
    except Exception:
        return None


def generate(event: dict) -> dict:
    """Returnează {what, where, when, severity_reason, recommended_action, source}."""
    event = event or {}
    rule = RULES.get(event.get("type", ""), _DEFAULT)
    report = {
        "what": rule["what"],
        "where": event.get("zone") or event.get("camera") or "zona necunoscuta",
        "when": event.get("timestamp") or datetime.now(timezone.utc).isoformat(),
        "severity_reason": rule["severity_reason"],
        "recommended_action": rule["recommended_action"],
        "source": "rules-fallback",
    }
    rephrased = _rephrase_with_llm(report)
    if rephrased:
        report.update(rephrased)
        report["source"] = "llm"
    return report


def summarize(report: dict) -> str:
    """2–3 propoziții din cifrele raportului de tură."""
    total = report.get("total", 0)
    by_severity = report.get("by_severity", {})
    by_type = report.get("by_type", {})
    escalated = report.get("escalated", 0)
    rid = by_severity.get("ridicata", 0)
    med = by_severity.get("medie", 0)
    types = ", ".join(f"{k}: {v}" for k, v in by_type.items()) or "niciun tip"
    return (
        f"In aceasta tura au fost inregistrate {total} evenimente de siguranta: "
        f"{rid} cu severitate ridicata si {med} cu severitate medie. "
        f"Repartitia pe tipuri: {types}. "
        f"Dintre acestea, {escalated} au fost escaladate catre coordonator."
    )


def slack_text(event: dict, escalated: bool) -> str:
    """Text Slack: severitate, tip, cameră/zonă, oră locală și link; fără imagini/butoane."""
    event = event or {}
    rule = RULES.get(event.get("type", ""), _DEFAULT)
    parts = [
        f"[{rule['severity'].upper()}]",
        rule["what"],
        f"Zona: {event.get('zone') or event.get('camera') or 'necunoscuta'}",
        f"Ora: {event.get('timestamp') or datetime.now(timezone.utc).isoformat()}",
    ]
    if event.get("link"):
        parts.append(f"Detalii: {event['link']}")
    if escalated:
        parts.append("ESCALADAT catre coordonator")
    return " | ".join(parts)


if __name__ == "__main__":
    # Fixture de demo: generează un raport dintr-un eveniment de test.
    fixture = {"type": "fod", "camera": "cam01", "zone": "taxiway A"}
    report = generate(fixture)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(slack_text(fixture, escalated=False))
    print(summarize({"total": 3, "by_severity": {"ridicata": 2, "medie": 1},
                     "by_type": {"fod": 1, "restricted_zone": 1, "no_ppe": 1},
                     "escalated": 1}))
