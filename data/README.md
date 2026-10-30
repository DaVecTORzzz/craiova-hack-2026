# data/ — video-uri și adnotări de test

Materialele grele stau în folderul comun din Drive, nu în git. Aici rămân doar README-urile cu sursă și licență.

## Structura în Drive

```text
SafeTarmac/
  data/
    videos/
      restricted_zone/
      no_ppe/
      fod/
      smoking/
      broll/
    annotations/
    reference_frames/
```

- `videos/` — câte un clip verificat pentru fiecare caz din demo.
- `annotations/` — etichete în format YOLO pentru clasele ad-hoc.
- `broll/` — material de context pentru pitch (avion, apron, echipă), nu intrare pentru detector.
- `reference_frames/` — cadru curat pentru FOD, din același unghi cu clipul.

Nume fișier: `YYYY-MM-DD_<caz>_<camera>_<descriere>.mp4`.

După upload, Dalina adaugă un rând în `videos/README.md` sau `annotations/README.md` cu sursa, licența, cine a filmat/adnotat și data. Fără acord scris, materialul nu se publică.
