# Craiova Hackathon 2026

Repo de lucru pentru hackathonul de la Craiova.
**Status: idei + schelet.** Nimic implementat încă.

## Idei principale

1. **Live Fact Checking** — verificarea în timp real a unui discurs (ex. dezbatere) și semnalarea afirmațiilor false.
2. **Workplace Safety AI** — încă neclarificat (monitorizare? raportare? conformitate?).

## Direcție tehnică (propunere)

- **Transcriere / speech-to-text**: local sau remote. Modelele pentru română nu sunt ideale, dar funcționează acceptabil. Nu e partea cea mai grea.
- **Debate + decider**: partea cea mai grea de rulat. Modele tip Qwen nu merg bine pe hardware slab → mai degrabă **remote**.
- **Logical fallacies**: multă lume face erori de logică într-un discurs, deci putem să le explicăm, nu doar să dăm un verdict.
- **Minimalist și local-first**: fără mail, datele stocate pe PC-ul userului.

## Întrebări deschise (de lămurit înainte de cod)

- Cine furnizează modelele AI: oferim noi serviciul, sau userul își aduce propriul supply (login pe Claude / ChatGPT)?
- Dacă facem concursuri de debate, cum obțin concurenții modelele pe care rulează soft-ul?
- Ce antrenăm, ce folosim, cum folosim, unde rulăm — adică ce înseamnă concret „AI" în proiectul ăsta.
- Self-supply e mai greu pentru useri, dar ne-ar permite să antrenăm un LLM pe date multe, axat strict pe fact checking.

## Organizare pe roluri

Propusă de Claudiu — **nu este finală** (există și varianta lui Andrei).

| Rol | Persoană | Status |
| --- | --- | --- |
| Model AI / research | TBD | deschis |
| Backend | TBD | deschis |
| Prezentare | TBD | deschis |
| Testare + test case-uri | TBD | deschis |

## Componente

| Componentă | Stare | Note |
| --- | --- | --- |
| Model AI (STT) | TBD | local vs. remote; calitate medie pe română |
| Model AI (debate / decider) | TBD | cel mai greu; probabil remote |
| Backend | TBD | de definit |
| Prezentare | TBD | de definit |
| Testare + test case-uri | TBD | de definit |

## Structura repo

```
.
├── .gitignore
└── README.md
```

## Link-uri

- Repo: <https://github.com/DaVecTORzzz/craiova-hack-2026>
