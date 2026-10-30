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

## Fișiere

| Clasă | Fișier | Sursă | Licență | Cine a adnotat | Data |
|---|---|---|---|---|---|
| `person` | de completat | de completat | de completat | de completat | de completat |
| `hi_vis_vest` | de completat | de completat | de completat | de completat | de completat |
| `hard_hat` | de completat | de completat | de completat | de completat | de completat |
| `ear_defender` | de completat | de completat | de completat | de completat | de completat |
| `fod_object` | de completat | de completat | de completat | de completat | de completat |
| `cigarette` | de completat | de completat | de completat | de completat | de completat |
| `smoke` | de completat | de completat | de completat | de completat | de completat |

Reguli: un singur format pentru toate clasele, împărțire train/validare pe surse diferite, fără fețe identificabile în seturile publicate.
