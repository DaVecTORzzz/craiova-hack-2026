# Video-uri de test

Câte un clip pentru fiecare caz din demo. Clipurile `.mp4` nu intră în git; le păstrăm în folderul comun din Drive, sub `SafeSight/data/videos/`.

| Caz | Fișier (în Drive) | Sursă | Licență | Cine a filmat | Data |
|---|---|---|---|---|---|
| Persoană în zona motorului | `videos/2026-10-30_restricted-zone_cam01_persoana-langa-motor.mp4` | de completat | de completat | de completat | 2026-10-30 |
| Persoane lângă motor la pushback | `videos/2026-10-30_restricted-zone_cam02_lucratori-pushback-motor..mp4` | de completat | de completat | de completat | 2026-10-30 |
| B-roll marshaller cu conuri | `videos/2026-10-30_broll_cam01_marshaller-conuri-apron.mp4` | de completat | de completat | de completat | 2026-10-30 |
| B-roll avion la poarta de bagaje | `videos/2026-10-30_broll_cam02_avion-la-poarta-bagaje.mp4` | de completat | de completat | de completat | 2026-10-30 |
| B-roll lucrători cu veste pe apron | `videos/2026-10-30_broll_cam03_lucratori-cu-veste-apron.mp4` | de completat | de completat | de completat | 2026-10-30 |
| B-roll tractor de bagaje | `videos/2026-10-30_broll_cam04_tractor-bagaje-apron.mp4` | de completat | de completat | de completat | 2026-10-30 |

## Reguli

- Un clip cu avionul în față, **fără persoană, PPE, FOD sau fum**, este B-roll pentru pitch. Nu se folosește ca test de detecție.
- Numele fișierului: `YYYY-MM-DD_<caz>_<camera>_<descriere>.mp4`.
- După upload, completează rândul din tabel cu sursa, licența, cine a filmat și data.
- Acord scris pentru voluntari; fețele se blurează înainte de publicare.
- FOD se filmează din același unghi cu cadrul de referință.

## Setul curent

Sunt 4 clipuri B-roll și 2 clipuri `restricted-zone`. Lipsește încă:

- clip video pentru PPE lipsă;
- clip video pentru FOD, din același unghi cu cadrul de referință.

`reference_frames/` are 4 cadre, iar `annotations/` are 4 etichete YOLO preliminare pentru PPE/FOD; ambele trebuie confirmate de A înainte de antrenare.

Numele `...pushback-motor..mp4` are două puncte; de corectat la următorul upload.
