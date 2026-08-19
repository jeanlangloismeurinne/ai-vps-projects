---
id: 1787053214093
type: feature
status: closed
closed_at: 2026-08-19T10:20:00Z
priority: medium
date: 2026-08-18T11:40:14.094331
project: bank-review
url: 
---

## ✨ Feature

**Date** : 18/08/2026 11:40
**URL** : `N/A`

### Description

Lorsqu’il y a des entrées positives dans des catégories qui correspondent à des dépenses (i.e. pas classées dans les sections correspondant aux entrées), j’aimerais avoir un petit chiffre dans la case correspondante avec la somme des entrées. Par exemple en vert clair en haut à droite de la case. Le texte ne doit pas masquer le texte de la case correspondant au total toute entrée+dépense confondue.

### Notes d'implémentation

`get_monthly_actuals` renvoie désormais un 3e dict `positives` (SQL `SUM(amount) FILTER (WHERE amount > 0)` par catégorie/mois), propagé via `build_budget_view(positives=…)` jusqu'à `m.positive` dans chaque cellule. Dans `budget.html`, les cellules de catégories de **dépense** (`not cat.is_income`, mois non futur) portent `position:relative` et affichent un badge `<span>` vert clair positionné en haut à droite (`+{{ m.positive|fmtnum }}`, `pointer-events:none` pour ne pas gêner le drill-down). Le total net `m.actual` reste affiché et non masqué.

Vérifié : `py_compile` OK sur `services/budget.py` et `routes/budget.py` ; template Jinja compile (filtres bouchonnés). Rendu visuel à confirmer en prod après déploiement.
