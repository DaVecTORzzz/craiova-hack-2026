# Dalina — notițe preliminare, 31 octombrie 2026

Am verificat eu `SafeSight/data` ca să nu pierdem timp. Nu sunt confirmate de tine; dacă vreuna nu se potrivește, corectează direct.

## Ce arată bine

- `videos/`: 6 clipuri — 4 B-roll și 2 `restricted-zone`. Numele respectă convenția, în afară de unul.
- `reference_frames/`: 4 cadre, toate 2752×1536. Perechea FOD e din același unghi; am interpretat `cam01` ca „cu vestă, fără cască” și `cam02` ca „cu cască, fără vestă” — confirmă.
- `README`-ul de video e actualizat cu fișierele curente.

## De confirmat / completat

1. `2026-10-30_restricted-zone_cam02_lucratori-pushback-motor..mp4` are două puncte; de redenumit în `...pushback-motor.mp4`.
2. `annotations/` e gol. Am lăsat `classes.txt` și formatul YOLO în `data/annotations/README.md`; nu am adnotat eu cadrele.
3. Pentru demo lipsesc clipuri video pentru PPE și FOD. Cadrele din `reference_frames/` sunt bune pentru referință/adnotare, dar nu înlocuiesc un clip pentru A.
4. Completează sursa, licența și cine a filmat pentru clipuri și cadre.
5. Confirmă că `restricted-zone_cam01_persoana-langa-motor.mp4` este inputul pentru primul slice A.

Nu e blocking pentru primul slice (`restricted-zone`), dar PPE și FOD nu pot intra în demo fără punctele 2 și 3.

Am făcut eu: README-ul de video, `reference_frames/README.md`, `classes.txt` și exemplul de format YOLO.
