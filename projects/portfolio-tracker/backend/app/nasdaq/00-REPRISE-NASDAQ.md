# Reprise — sous-projet NASDAQ

**Sous-projet indépendant, sorti du chantier V3 le 2026-11-13** (arbitrage de l'utilisateur). Il ne lit
ni n'écrit rien du reste du système ; il pourra devenir un jour une partie d'un module de sélection des
titres. Ce qu'il fait et ce qui le garde : `ARCHITECTURE.md` (même dossier), `check_nasdaq_proba.py`.

## Reste à faire

- Appliquer à la main les deux migrations (jamais auto-appliquées, convention #17) :
  `backend/app/db/migrations/nasdaq_01_suivi.sql` puis `nasdaq_02_watchlist_proba.sql`
  (`docker cp … shared-postgres:/tmp/ && docker exec shared-postgres psql -U admin -d db_portfolio -f /tmp/…`).
  État en production **non vérifié** depuis une session sans accès à la base.

Aucun autre développement prévu avant le premier comité.
