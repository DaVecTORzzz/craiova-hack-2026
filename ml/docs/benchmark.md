# Benchmark — edge

Se completează după prima rulare pe hardware-ul de demo. Nu se inventează cifre.

| Data | Hardware | Model | FPS | Detecție → eveniment | Note |
|---|---|---|---|---|---|
| de măsurat | laptop demo / Jetson | `yolo26n.pt` | de măsurat | de măsurat | clip real, nu sintetic |

## Cum se măsoară

- FPS: numărul de cadre procesate împărțit la durata reală a rulării.
- Detecție → eveniment: timestamp-ul evenimentului minus începutul cadrului în care regula a fost confirmată.
- Se notează și rezoluția, `imgsz`, dacă s-a folosit GPU și dacă a rulat și blur-ul de fețe.

## Rezultatul intră în

- `docs/benchmark.md` din repo-ul public, pentru pitch;
- raportul de tură și slide-ul de tehnologie al lui D.
