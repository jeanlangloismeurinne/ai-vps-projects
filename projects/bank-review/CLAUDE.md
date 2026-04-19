# CLAUDE.md — bank-review

## Conventions métier

### Années fiscales
Les onglets "suivi budget" (`budget_years`) sont des **années fiscales Sep 1 → Août 31**, pas des années calendaires.
Ex : `2024-2025` = 2024-09-01 → 2025-08-31. Le label suit le pattern `YYYY-YYYY`.

Toute création automatique de période doit prolonger la dernière en utilisant `end_date + 1 jour` comme `start_date`, et conserver la même durée que la période précédente.
