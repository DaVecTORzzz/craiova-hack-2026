# Dalina — notițe preliminare, 31 octombrie 2026

Am verificat eu `SafeSight/data` ca să nu pierdem timp. Nu sunt confirmate de tine; dacă vreuna nu se potrivește, corectează direct.

## Ce arată bine

- `videos/`: 6 clipuri — 4 B-roll și 2 `restricted-zone`. Numele respectă convenția, în afară de unul.
- `reference_frames/`: 2 cadre PPE, ambele 2752×1536. Am interpretat `cam01` ca „cu vestă, fără cască” și `cam02` ca „cu cască, fără vestă” — confirmă.
- `README`-ul de video e actualizat cu fișierele curente.

## De confirmat / completat

1. `2026-10-30_restricted-zone_cam02_lucratori-pushback-motor..mp4` are două puncte; de redenumit în `...pushback-motor.mp4`.
2. `annotations/` era gol la data notiței; acum are 2 etichete validate vizual de Andrei (vezi `data/annotations/README.md`).
3. Pentru demo lipsesc clipuri video pentru PPE. Cadrele din `reference_frames/` sunt bune pentru referință/adnotare, dar nu înlocuiesc un clip pentru A.
4. Completează sursa, licența și cine a filmat pentru clipuri și cadre.
5. Confirmă că `restricted-zone_cam01_persoana-langa-motor.mp4` este inputul pentru primul slice A.

Nu e blocking pentru primul slice (`restricted-zone`), dar PPE nu poate intra în demo fără punctele 2 și 3.

Am făcut eu: README-ul de video, `reference_frames/README.md`, `classes.txt` și exemplul de format YOLO.
