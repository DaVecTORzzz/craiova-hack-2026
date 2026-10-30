# Reguli pentru asistenții AI din acest repo

Proiect de hackathon: SafeTarmac AI, siguranță pe platforma aeroportului. Patru oameni lucrează în paralel, fiecare în folderul lui, fiecare cu asistentul lui AI. Aceste reguli există ca să nu vă stricați munca unul altuia.

## Reguli obligatorii

1. **Modifică doar folderul persoanei care lucrează cu tine.** `ml/` Andrei, `backend/` Max, `automation/` Dalina, `frontend/` Ariana. Dacă o schimbare cere modificări în alt folder, spune-i utilizatorului și propune un issue; nu face tu modificarea.
2. **`docs/contract.md` e sursa de adevăr.** Folosește exact numele de câmpuri, valorile și endpoint-urile de acolo. Edge nu trimite `status` sau `report`; `snapshot_url` e HTTP, niciodată `minio://`; `confidence` e obiect `{detector, temporal}`. Nu modifica contractul decât dacă utilizatorul cere explicit, și atunci doar într-un pull request separat.
3. **Nu pune secrete în cod sau în git.** Cheile se citesc din variabile de mediu (vezi `.env.example`). Nu crea și nu comite fișiere `.env`.
4. **Nu comite fișiere mari:** video-uri, modele (`.pt`, `.onnx`), baze de date. Sunt în `.gitignore`.
5. **Confidențialitate:** nu salva și nu afișa imagini cu fețe neblurate. Nu identifica persoane; folosește doar ID-ul de tracking („persoana #17”).
6. **`main` trebuie să ruleze.** Lucrează pe un branch, cu commit-uri mici și prefix (`ml:`, `api:`, `ui:`, `auto:`, `docs:`).

## Stack

- Python 3.12, `uv`, FastAPI, Pydantic v2, SQLite, OpenCV
- Ultralytics YOLO26 cu tracking-ul încorporat (`model.track(..., tracker="bytetrack.yaml")`); `sv.ByteTrack` nu mai există în supervision ≥ 0.31
- Blur pe fețe cu OpenCV YuNet (`cv2.FaceDetectorYN`)
- Frontend: React 19 + Vite 8 + TypeScript, Tailwind CSS v4, TanStack Query v5
- Notificări: Slack incoming webhook, text + link, fără imagini și fără butoane

Verifică versiunile exacte în `pyproject.toml` / `package.json` ale fiecărui modul înainte să scrii cod care depinde de un API anume.
