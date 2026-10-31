# Adnotări

Etichete în format YOLO (`.txt` lângă imagine, coordonate normalizate), pentru clasele ad-hoc din demo.

## Mapare clase

Ordinea din `classes.txt` este contractul cu A. Nu o schimba fără să întrebi.

| ID | Clasă |
|---|---|
| 0 | `person` |
| 1 | `hi_vis_vest` |
| 2 | `hard_hat` |
| 3 | `ear_defender` |
| 4 | `fod_object` |
| 5 | `cigarette` |
| 6 | `smoke` |

## Format

Un rând per obiect: `class_id x_center y_center width height`, toate coordonatele normalizate 0–1.

Exemplu de format (nu este o adnotare reală):

```text
0 0.512 0.431 0.184 0.522
1 0.512 0.500 0.150 0.220
```

## Set actual (validat)

Etichetele de mai jos sunt făcute de Andrei pe cele 4 cadre din `reference_frames/`. Au fost verificate de Dalina și **validate vizual de Andrei pe 31 octombrie 2026**, pe overlay-urile din `review/`. Setul este valid pentru demo și experimente, nu pentru antrenare de producție.

| Imagine | Label | Conținut |
|---|---|---|
| `2026-10-30_no-ppe_cam01_fara-casca.jpeg` | `2026-10-30_no-ppe_cam01_fara-casca.txt` | `person`, `hi_vis_vest`; fără `hard_hat` |
| `2026-10-30_no-ppe_cam02_fara-vesta.jpeg` | `2026-10-30_no-ppe_cam02_fara-vesta.txt` | `person`, `hard_hat`; fără `hi_vis_vest` |
| `2026-10-30_fod_cam01_asfalt-curat.jpeg` | `2026-10-30_fod_cam01_asfalt-curat.txt` | fișier gol, exemplu negativ |
| `2026-10-30_fod_cam01_sticla-pe-asfalt.jpeg` | `2026-10-30_fod_cam01_sticla-pe-asfalt.txt` | `fod_object` pe sticlă |

Overlay-urile de verificare sunt în `review/` și nu intră în git. Fluxul complet, cu exact pașii și snippet-urile folosite, este în [`docs/agentic-annotation-workflow.md`](../../docs/agentic-annotation-workflow.md).

## Validare

- **31 octombrie 2026**, Andrei a deschis cele 4 overlay-uri din `review/` și a confirmat boxele și clasele. Coordonatele nu au fost modificate; validarea a confirmat fișierele existente.
- `no-ppe_cam01`: `person` + `hi_vis_vest`; absența `hard_hat` este corectă.
- `no-ppe_cam02`: `person` + `hard_hat`; absența `hi_vis_vest` este corectă.
- `fod_cam01_asfalt-curat`: fișier gol, exemplu negativ corect.
- `fod_cam01_sticla-pe-asfalt`: `fod_object` acoperă sticla.
- Setul rămâne mic și nu înlocuiește un dataset de antrenare.

## Fișiere

| Clasă | Sursă | Licență | Cine a adnotat | Data |
|---|---|---|---|---|
| `ear_defender` | de completat | de completat | — | — |
| `cigarette` | de completat | de completat | — | — |
| `smoke` | de completat | de completat | — | — |
| `person` | Gemini (imagine sintetică, generată de echipă) | internă — nu se publică | Andrei (adnotare + validare), Dalina (verificare) | 2026-10-31 |
| `hi_vis_vest` | Gemini (imagine sintetică, generată de echipă) | internă — nu se publică | Andrei (adnotare + validare), Dalina (verificare) | 2026-10-31 |
| `hard_hat` | Gemini (imagine sintetică, generată de echipă) | internă — nu se publică | Andrei (adnotare + validare), Dalina (verificare) | 2026-10-31 |
| `fod_object` | Gemini (imagine sintetică, generată de echipă) | internă — nu se publică | Andrei (adnotare + validare), Dalina (corectare cutie) | 2026-10-31 |

Reguli: un singur format pentru toate clasele, împărțire train/validare pe surse diferite, fără fețe identificabile în seturile publicate.
