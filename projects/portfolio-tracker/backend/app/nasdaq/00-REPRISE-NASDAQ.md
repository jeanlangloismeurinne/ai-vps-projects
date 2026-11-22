# Reprise — sous-projet NASDAQ

**Sous-projet indépendant, sorti du chantier V3 le 2026-11-13** (arbitrage de l'utilisateur). Il ne lit
ni n'écrit rien du reste du système. Ce qu'il fait et ce qui le garde : `ARCHITECTURE.md` (même dossier),
`check_nasdaq_proba.py`, `check_nasdaq_valeur.py` (+ `negatif_nasdaq_valeur.sh`).

## État (2026-11-22)

- Migrations `nasdaq_01`, `nasdaq_02`, `nasdaq_03_valeur` appliquées en production.
- « Valeur du temps passé » livrée : plancher indexé, décomposition de la hausse, PER à terme ; parcours C
  (badge des cartes → onglet Valeur de la fiche ; page comparative `/nasdaq/valeur`). Maquette d'arbitrage :
  https://claude.ai/artifact/X9dAau3SQUAFSUBrJghf56.

## Reste à faire

- Arbitrer « bénéfice publié ou d'exploitation » (plus-values sur participations d'Alphabet et d'Amazon en 2026).
- Émetteurs étrangers (20-F) : bénéfice annuel seulement, l'état retarde jusqu'à un an (ASML).
- Le consensus à terme n'a d'historique qu'à partir du 2026-11-22 (photo hebdomadaire).
