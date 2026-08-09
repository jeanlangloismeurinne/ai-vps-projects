---
id: 1786259000000
type: feature
status: open
priority: high
date: 2026-08-09T00:00:00.000000
project: portfolio-tracker
milestone: roadmap-1783146342816
---

## ✨ Gate d'opportunité obligatoire avant création de thèse

**Date** : 09/08/2026

### Description

Rendre l'analyse d'opportunité obligatoire avant la création d'une thèse. Actuellement `opportunity_id` est `Optional[int]` dans `thesis_v2.py` (l. 47), ce qui permet de créer une thèse sans aucun screening préalable. De plus, même si un brief existe avec `recommendation = 'PASS'`, rien n'empêche de créer une thèse dessus.

**Comportement attendu** :
- `POST /tickers/{id}/theses` : `opportunity_id` devient obligatoire (non-nullable) sauf si le payload est de type `ImportLegacyBody`
- Si `opportunity_id` est fourni mais que le brief référencé a `recommendation ≠ 'PROCEED'` : retourner HTTP 422 avec message explicite ("Ce brief a une recommandation PASS — relancer une analyse ou valider manuellement avant de créer une thèse")
- Si `opportunity_id` est fourni et `recommendation = 'PROCEED'` : comportement inchangé

**Ce qui ne change pas** :
- L'endpoint `POST /tickers/{id}/theses` avec `ImportLegacyBody` (import legacy) — pas de validation d'opportunity_id
- Les thèses déjà créées sans opportunity_id — données existantes inchangées

**Frontend** :
- Page watchlist-v2 : le bouton "Lancer la thèse" doit passer par la Page 3 d'opportunité si pas de brief PROCEED existant, ou afficher un message explicatif
- Page 4 (thesis) : si arrivée directe sans brief, afficher un overlay ou redirect vers Page 3

**Fichiers à modifier** :
- `backend/app/api/thesis_v2.py` — validation `opportunity_id` + check `recommendation`
- `backend/app/db/models.py` — rendre `opportunity_id` non-optional dans le body de création (ou gérer via une validation explicite dans le handler)
- `frontend/pages/watchlist-v2.js` — adapter le flow de navigation
- `frontend/pages/ticker/[ticker_id]/thesis/[thesis_id].js` — gestion cas sans brief

**Hors-scope** :
- Modifier le mécanisme de validation de thèse (POST /theses/{id}/validate)
- Changer la logique de statut du brief (`validated`/`dismissed`/etc.)
