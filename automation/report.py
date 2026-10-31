"""Raport AI pentru SafeSight — generează textele, nu trimite nimic.

Backend-ul deține ingestia, escaladarea și trimiterea efectivă către Slack.
Acțiunea recomandată vine din tabelul fix pe tip; LLM-ul doar reformulează.
Dacă LLM-ul lipsește sau pică, se folosește fallback-ul pe reguli.

Contractul cu backend-ul:
- ``generate`` primește un ``EventOut`` (``type`` uppercase, ``zone_id``,
  ``camera_id``, ``detected_at``, ``duration_s``) și întoarce exact câmpurile
  din ``ReportOut``; ``source`` este doar ``template`` sau ``llm``.
- ``summarize`` primește raportul de tură al backend-ului, cu ``kpi`` și
  ``by_type`` ca listă de dict-uri.
- ``slack_text`` primește opțional ``link`` și ``escalate_after_s`` de la
  backend, ca textul să folosească URL-ul configurat acolo.
"""

import json
import os
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

try:
    LOCAL_TZ = ZoneInfo("Europe/Bucharest")
except Exception:
    from datetime import timedelta
    LOCAL_TZ = timezone(timedelta(hours=2))

# Tabelul fix pe tip de eveniment: acțiunea recomandată NU vine de la LLM.
RULES = {
    "RESTRICTED_ZONE": {
        "severity": "CRITICAL",
        "what": "Persoană în zona restricționată (motor).",
        "severity_reason": "Zonă restricționată activă; risc de accident.",
        "recommended_action": "Oprește activitatea în zonă și contactează persoana prin radio.",
    },
    "NO_PPE": {
        "severity": "WARNING",
        "what": "Echipament de protecție lipsă pe apron.",
        "severity_reason": "Lucru fără echipamentul obligatoriu.",
        "recommended_action": "Supervizorul verifică echipamentul persoanei înainte de reluarea lucrului.",
    },
    "FOD": {
        "severity": "CRITICAL",
        "what": "Obiect străin (FOD) pe suprafața de mișcare.",
        "severity_reason": "Obiectele uitate pot fi aspirate de motoare.",
        "recommended_action": "Inspectează și îndepărtează obiectul înainte de următoarea mișcare.",
    },
    "SMOKING": {
        "severity": "WARNING",
        "what": "Posibil fumat în zona aeronavei.",
        "severity_reason": "Fumatul lângă aeronave și combustibil e interzis.",
        "recommended_action": "Supervizorul verifică imediat situația la fața locului.",
    },
    "CAMERA_OFFLINE": {
        "severity": "WARNING",
        "what": "Camera nu mai transmite cadre.",
        "severity_reason": "Zona nu mai e supravegheată.",
        "recommended_action": "Verifică alimentarea și rețeaua camerei.",
    },
}

_DEFAULT = {
    "severity": "WARNING",
    "what": "Eveniment de siguranță nespecificat.",
    "severity_reason": "Tip de eveniment necunoscut; necesită verificare umană.",
    "recommended_action": "Un operator uman verifică imaginile și decide acțiunea.",
}

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def _event_type(event: dict) -> str:
    raw = event.get("type") or event.get("event_type") or ""
    raw = getattr(raw, "value", raw)
    return str(raw).strip().upper()


def _event_time(event: dict) -> datetime:
    raw = event.get("detected_at") or event.get("timestamp")
    parsed = None
    if isinstance(raw, datetime):
        parsed = raw
    elif isinstance(raw, str) and raw.strip():
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            parsed = None
    if parsed is None:
        parsed = datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(LOCAL_TZ)


def _where(event: dict) -> str:
    camera = event.get("camera_id") or event.get("camera")
    zone = event.get("zone_id") or event.get("zone")
    if camera and zone:
        return f"Camera {camera}, zona {zone}."
    if camera:
        return f"Camera {camera}."
    if zone:
        return f"Zona {zone}."
    return "Zona necunoscută."


def _when(event: dict) -> str:
    when = _event_time(event).strftime("%H:%M:%S")
    duration = event.get("duration_s")
    if isinstance(duration, (int, float)):
        when += f", timp în zonă {duration:.1f} s"
    return when + "."


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
    except Exception:
        return None
    if not isinstance(rephrased, dict):
        return None
    fields = ("what", "severity_reason", "recommended_action")
    if not all(isinstance(rephrased.get(k), str) and rephrased[k].strip() for k in fields):
        return None
    return {k: rephrased[k].strip() for k in fields}


def generate(event: dict) -> dict:
    """Returnează {what, where, when, severity_reason, recommended_action, source}."""
    event = event or {}
    rule = RULES.get(_event_type(event), _DEFAULT)
    report = {
        "what": rule["what"],
        "where": _where(event),
        "when": _when(event),
        "severity_reason": rule["severity_reason"],
        "recommended_action": rule["recommended_action"],
        "source": "template",
    }
    rephrased = _rephrase_with_llm(
        {k: report[k] for k in ("what", "where", "when", "severity_reason", "recommended_action")}
    )
    if rephrased:
        report.update(rephrased)
        report["source"] = "llm"
    return report


def _type_counts(by_type: object) -> tuple[int, int, int]:
    """Întoarce (total, critical, warning) din forma backend-ului sau din dict."""
    if isinstance(by_type, dict):
        total = sum(int(value or 0) for value in by_type.values())
        return total, 0, 0
    critical = warning = 0
    if isinstance(by_type, list):
        for row in by_type:
            if not isinstance(row, dict):
                continue
            critical += int(row.get("critical") or 0)
            warning += int(row.get("warning") or 0)
    return critical + warning, critical, warning


def _plural(count: int, one: str, many: str) -> str:
    return one if count == 1 else many


SHIFT_LABELS = {"morning": "de dimineață", "afternoon": "de după-amiază", "night": "de noapte"}


def summarize(report: dict) -> str:
    """2–3 propoziții din cifrele raportului de tură al backend-ului."""
    report = report or {}
    total, critical, warning = _type_counts(report.get("by_type"))
    kpi = report.get("kpi") or {}
    open_incidents = int(kpi.get("open_incidents") or report.get("open_incidents") or 0)
    escalated = int(kpi.get("escalated") or report.get("escalated") or 0)
    shift = SHIFT_LABELS.get(report.get("shift"), report.get("shift") or "curentă")
    day = report.get("date") or "necunoscută"
    return (
        f"Tura {shift} din {day}: {total} {_plural(total, 'eveniment', 'evenimente')}, "
        f"{critical} {_plural(critical, 'critic', 'critice')} și {warning} de avertizare. "
        f"{open_incidents} {_plural(open_incidents, 'rămâne deschis', 'rămân deschise')}, "
        f"iar {escalated} {_plural(escalated, 'a fost escaladat', 'au fost escaladate')}."
    )


def slack_text(event: dict, escalated: bool) -> str:
    """Text Slack: severitate, tip, cameră/zonă, oră locală și link; fără imagini/butoane."""
    event = event or {}
    event_type = _event_type(event) or "EVENIMENT"
    rule = RULES.get(event_type, _DEFAULT)
    severity = str(event.get("severity") or rule["severity"]).upper()
    camera = event.get("camera_id") or event.get("camera") or "necunoscută"
    zone = event.get("zone_id") or event.get("zone") or "necunoscută"
    parts = [
        f"[{severity}] {event_type}",
        f"{camera} / {zone}",
        _event_time(event).strftime("%H:%M:%S"),
    ]
    link = event.get("link")
    if link:
        parts.append(str(link))
    text = " · ".join(parts)
    if escalated:
        seconds = event.get("escalate_after_s")
        prefix = f"ESCALADARE · neconfirmat de {seconds} s · " if seconds is not None else "ESCALADARE · "
        text = prefix + text
    return text


if __name__ == "__main__":
    # Fixture de demo: generează un raport dintr-un eveniment de test.
    fixture = {
        "event_id": "evt_demo_1",
        "type": "FOD",
        "severity": "CRITICAL",
        "camera_id": "taxiway-b",
        "zone_id": "taxiway-b",
        "detected_at": "2026-10-31T10:42:13Z",
        "duration_s": 3.0,
    }
    generated = generate(fixture)
    print(json.dumps(generated, ensure_ascii=False, indent=2))
    print(slack_text({**fixture, "link": "http://localhost:5173/incidents/evt_demo_1"}, escalated=False))
    print(
        summarize(
            {
                "shift": "morning",
                "date": "2026-10-31",
                "kpi": {"open_incidents": 2, "escalated": 1},
                "by_type": [
                    {"type": "FOD", "critical": 1, "warning": 0},
                    {"type": "NO_PPE", "critical": 0, "warning": 4},
                ],
            }
        )
    )
