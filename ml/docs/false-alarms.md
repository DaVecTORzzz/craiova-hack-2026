# Eșantion de falsuri — 5 evenimente

Data: 31 octombrie 2026. Nu este o rată de falsuri; este inventarul complet al evenimentelor produse de cele două clipuri reale.

## Metodă

- `restricted-zone_cam01` și `restricted-zone_cam02`, rulate integral;
- `fixtures/zones.stand12.json`, `engine_on=true`, dry-run;
- evenimentele au fost extrase din `metrics.json` (`event_details`);
- fiecare snapshot blurat a fost verificat vizual: persoana este în zona configurată.
- TP = persoană prezentă în zona configurată; `cam02` nu are poligon calibrat propriu, deci eticheta nu validează geometria pe acea cameră.

## Rezultat

| Clip | Track | Confidence | Etichetă | Notă |
|---|---:|---:|---|---|
| `restricted-zone_cam01` | 3 | 0,55 | TP | persoană în zona motorului |
| `restricted-zone_cam01` | 4 | 0,40 | TP | persoană în zona motorului |
| `restricted-zone_cam02` | 1 | 0,75 | TP | persoană lângă trenul de aterizare |
| `restricted-zone_cam02` | 2 | 0,68 | TP | persoană lângă trenul de aterizare |
| `restricted-zone_cam02` | 8 | 0,44 | TP | persoană în cadru, în zona configurată |

**Total: 5 TP, 0 FP.**

## Ce nu intră în calcul

- B-roll-ul nu este caz de detecție; evenimentele lui cu poligonul `stand12` sunt un smoke de zonă, nu falsuri reale.
- Nu există clipuri PPE/FOD, deci nu există evenimente pentru ele.
- Cele două clipuri folosesc același poligon `stand12`; `cam02` nu are poligon calibrat propriu, deci eticheta TP este „în zona configurată”, nu validare geometrică pe camera 2.

## Interpretare

- Pe eșantionul de 5 evenimente nu au apărut false pozitive; toate cele 5 au persoană în zona configurată.
- Eșantionul este prea mic pentru o rată de falsuri credibilă; pentru 50–100 evenimente sunt necesare clipuri independente.
- Nu raporta „0% falsuri” în pitch. Spune: „5/5 evenimente reale confirmate pe cele două clipuri; rata de falsuri rămâne de măsurat.”
