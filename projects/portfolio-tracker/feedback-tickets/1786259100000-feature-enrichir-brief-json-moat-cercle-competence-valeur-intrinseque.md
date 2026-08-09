---
id: 1786259100000
type: feature
status: open
priority: high
date: 2026-08-09T00:00:00.000000
project: portfolio-tracker
milestone: roadmap-1783146342816
---

## ✨ Enrichir brief_json : moat + cercle de compétence + valeur intrinsèque

**Date** : 09/08/2026

### Description

Ajouter 3 blocs structurés dans `brief_json` pour combler les gaps majeurs identifiés vs. un processus d'investissement professionnel (type Buffett). Ces blocs capturent ce que l'analyse actuelle ne couvre pas : l'avantage concurrentiel durable, la clarté analytique sur le business, et la valeur fondamentale vs. prix.

**Nouveaux blocs à ajouter dans `brief_json`** :

```json
{
  "moat": {
    "score": 3,
    "description": "Avantage concurrentiel durable sur 10 ans — ex: switching costs, réseau, marque, coûts"
  },
  "cercle_competence": {
    "ok": true,
    "note": "Je comprends le modèle économique, les drivers de revenus et les risques sectoriels"
  },
  "valeur_intrinseque": {
    "fourchette_basse": 120,
    "fourchette_haute": 160,
    "methode": "FCF yield normalisé sur 10 ans avec croissance conservatrice",
    "marge_securite_pct": -15
  }
}
```

**Règle 3 points de synchronisation** — les 3 fichiers suivants doivent être mis à jour simultanément :
1. **Prompt Dust `opportunity-agent`** (table `agent_prompts` en DB) — le schéma JSON de sortie attendu
2. **Frontend** `components/InvestmentBriefEditor.js` — affichage et édition des nouveaux blocs
3. **Import legacy** `thesis_v2.py` (`ImportLegacyBody`) — accepter les nouveaux champs

**Détail des champs** :

`moat.score` : entier 1-5
- 1 = aucun avantage identifiable
- 3 = avantage réel mais contestable
- 5 = moat très solide (ex: réseau, réglementation, coûts de substitution prohibitifs)

`moat.description` : texte libre — nature du moat + durabilité estimée

`cercle_competence.ok` : booléen — "je comprends ce business suffisamment pour investir"
`cercle_competence.note` : explication courte — ce que l'analyste comprend ou ce qui reste opaque

`valeur_intrinseque.fourchette_basse` / `fourchette_haute` : estimation en devise de l'analyse
`valeur_intrinseque.methode` : méthode utilisée (FCF yield, multiples sectoriels, somme des parties…)
`valeur_intrinseque.marge_securite_pct` : calculé par l'agent → `(fourchette_basse - prix_actuel) / prix_actuel * 100`. Positif = décote, négatif = prime.

**Comportement du PASS renforcé** :
Le prompt doit indiquer que `recommendation = 'PASS'` est la réponse correcte si :
- `cercle_competence.ok = false` (pas dans le cercle de compétence)
- `moat.score < 2` (pas d'avantage défendable)
- `valeur_intrinseque.marge_securite_pct < -20` (prix > valeur intrinsèque haute)

**Fichiers à modifier** :
- `backend/app/api/opportunity.py` — extraction JSON enrichie (`refresh-json` endpoint)
- `frontend/components/InvestmentBriefEditor.js` — 3 nouvelles sections (moat, cercle, valeur intrinsèque)
- `backend/app/api/thesis_v2.py` — accepter les nouveaux champs dans `ImportLegacyBody`
- Prompt `opportunity-agent` en DB (via Page Admin) — voir règle des 3 points

**Hors-scope** :
- Modifier `ThesisEditorV2.js` (les nouvelles évaluations appartiennent au brief, pas à la thèse)
- Ajouter un calcul automatique côté backend (le calcul reste côté agent Dust)
- Champs PE/VC (les sociétés privées ont une logique de valorisation distincte, à traiter séparément)
