---
id: 1786259200000
type: feature
status: open
priority: medium
date: 2026-08-09T00:00:00.000000
project: portfolio-tracker
milestone: roadmap-1783146342816
---

## ✨ Injection du contexte portefeuille dans l'opportunity-agent

**Date** : 09/08/2026

### Description

Actuellement, l'opportunity-agent ne voit que les données du ticker analysé. Il ne peut pas répondre à la question fondamentale : "est-ce un meilleur usage de capital que ce que je possède déjà ?"

Injecter un résumé des positions actives dans le prompt `json_generation` pour permettre à l'agent d'évaluer le coût d'opportunité.

**Comportement attendu** :

Lors de l'appel `POST /opportunities/{id}/refresh-json`, le backend construit un bloc "portfolio_context" et l'injecte dans le message envoyé à Dust :

```
[portfolio_context]
Positions actives :
- NVDA (tech/semiconducteurs) : thèse active depuis 6 mois, perf +23%, conviction 8/10
- CAP (IT services) : thèse active depuis 3 mois, perf +8%, conviction 7/10
Cash disponible : 15% du portefeuille
[/portfolio_context]
```

**Nouveau champ dans `brief_json`** :
```json
{
  "opportunity_cost_note": "Comparé à NVDA (+23%) avec un moat solide, cette opportunité présente une prime de valorisation sans avantage concurrentiel comparable. Coût d'opportunité élevé."
}
```

**Source des données portefeuille** :
- `portfolio_positions` (status positions actives) + `theses` (conviction_score, perf calculée) via `portfolio_v2.py`
- Calcul de la perf : `(prix_actuel - purchase_price) / purchase_price * 100`
- Pas de données temps-réel forcées — utiliser le cache Redis existant (TTL 4h)

**Règle d'injection** :
- Si aucune position active → ne pas injecter le bloc (ne pas envoyer un contexte vide)
- Si position sans perf calculable (ticker_symbol NULL, société privée) → inclure avec mention "perf N/A"

**Fichiers à modifier** :
- `backend/app/api/opportunity.py` — endpoint `refresh-json` : construire et injecter le portfolio_context
- `backend/app/api/portfolio_v2.py` — extraire une fonction utilitaire retournant le résumé des positions
- `frontend/components/InvestmentBriefEditor.js` — afficher `opportunity_cost_note` (lecture seule, section distincte)
- Prompt `opportunity-agent` en DB — documenter la structure `[portfolio_context]` attendue en entrée et le champ `opportunity_cost_note` en sortie (règle 3 points de synchronisation)

**Hors-scope** :
- Modifier le mode `freeform` ou `conviction_challenge` (injection uniquement sur `json_generation`)
- Comparer avec les tickers en watchlist (uniquement les positions actives en portefeuille)
- Recalcul en temps réel de la perf (cache existant suffisant)
