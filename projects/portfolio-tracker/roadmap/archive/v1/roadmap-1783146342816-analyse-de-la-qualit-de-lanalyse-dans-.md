---
id: roadmap-1783146342816
status: tickets-created
created: 2026-07-04T06:25:42.816921
project: portfolio-tracker
---

## Analyse de la qualité de l’analyse dans un flux d’investissement

### Direction / Feature (utilisateur)
Je veux comparer le flux d’investissement actuel avec le flux qu’un professionnel type Warren Buffet réaliserait avant de prendre une décision d’allocation. 

L’objectif est d’auditer l’existant pour envisager des évolutions : création de nouveaux agents, modification des agents existants, ajouts de données, etc

En particulier, mon flux existant prévoit la création d’une thèse (en sautant très fréquemment l’étape d’analyse d’opportunité qui est trop succincte pour être pertinente). Mais du coup je ne suis pas sûr d’avoir un processus pour évaluer si cet investissement est meilleur ou moins bon qu’un autre. J’imagine que l’agent sait toujours définir une thèse pour un investissement alors qu’il faudrait que le système puisse conclure qu’il vaut mieux passer son tour.

---
### Spec générée

#### Audit du flux actuel

**Flux nominal** : watchlist → (Page 3 optionnelle) → Page 4 thèse → validation position → monitoring.

**Problèmes structurels identifiés** :

**1. L’étape opportunité est bypassable**
`opportunity_id` est `Optional[int]` dans `thesis_v2.py` (l. 47). Un utilisateur peut créer une thèse directement depuis la watchlist sans aucun screening préalable.

**2. La recommandation PASS n’a aucun effet**
Le champ `opportunity_briefs.recommendation = ‘PASS’` est stocké en DB mais aucune logique backend ne bloque la création de thèse si le brief référencé est PASS. C’est une donnée sans enforcement.

**3. Pas de valeur intrinsèque ni marge de sécurité**
Le `brief_json` contient `anomalie.score` (anomalie de prix) et `verdict.downside_floor` (plancher de baisse estimé) mais aucune fourchette de valeur intrinsèque ni de marge de sécurité calculée vs. prix actuel. L’anomalie de prix ≠ décote sur valeur fondamentale.

**4. Moat non évalué**
`anomalie` capture un écart de prix temporaire, pas un avantage concurrentiel durable. Aucun champ ne force à répondre à "pourquoi cette entreprise sera encore dominante dans 10 ans ?"

**5. Cercle de compétence non vérifié**
Aucun champ ne force l’utilisateur/l’agent à évaluer si le business est suffisamment compris pour investir dessus.

**6. Pas de coût d’opportunité**
L’opportunity-agent reçoit des données sur le ticker analysé mais ne voit pas le portefeuille actuel. Il ne peut pas répondre : "est-ce un meilleur usage de capital que ce que vous possédez déjà ?"

#### Comparaison avec le processus Buffett

| Étape Buffett | Système actuel | Gap |
|---|---|---|
| Cercle de compétence | Absent | ⚠ Champ manquant |
| Moat / avantage concurrentiel durable | Absent (`anomalie` ≠ moat) | ⚠ Champ manquant |
| Qualité du management | Absent | ❌ Non couvert (hors scope pour l’instant) |
| Analyse financière (ROIC, FCF, dette) | Partiel (données M1 disponibles mais non synthétisées dans le brief) | ~ Données disponibles |
| Valeur intrinsèque + marge de sécurité | Absent | ⚠ Champ manquant |
| Coût d’opportunité vs. alternatives | Absent (agent ne voit pas le portefeuille) | ⚠ Non injecté |
| Décision "passer son tour" | Partiel (PASS stocké, non enforced) | ⚠ Pas d’enforcement |

#### Évolutions proposées → tickets créés

**P1 — Gate d’opportunité obligatoire (haute priorité)**
Rendre `opportunity_id` obligatoire à la création de thèse et valider que le brief a `recommendation = ‘PROCEED’`. Le bypass n’est autorisé que pour l’endpoint legacy import (`ImportLegacyBody`).

**P2 — Enrichir le brief_json : moat + cercle de compétence + valeur intrinsèque (haute priorité)**
Ajouter 3 blocs dans `brief_json` :
- `moat` : `score` 1-5 + `description` de l’avantage concurrentiel durable
- `cercle_competence` : `ok: bool` + `note: str` (pourquoi je comprends ou pas ce business)
- `valeur_intrinseque` : `fourchette_basse`, `fourchette_haute`, `methode` (ex: "FCF yield normalisé"), `marge_securite_pct` (calculée : `(fourchette_basse - prix_actuel) / prix_actuel * 100`)

Règle 3 points de synchronisation : prompt Dust agent_prompts + InvestmentBriefEditor.js + import legacy.

**P3 — Injection contexte portefeuille dans l’opportunity-agent (moyenne priorité)**
Lors de l’appel `json_generation`, injecter un résumé des positions actives (ticker, perf actuelle, conviction thesis). Ajouter `opportunity_cost_note` dans `brief_json` — évaluation comparative vs. meilleures alternatives en portefeuille.

### Tickets créés

- `1786259000000` — feature — Gate opportunité obligatoire avant création de thèse
- `1786259100000` — feature — Enrichir brief_json : moat + cercle de compétence + valeur intrinsèque
- `1786259200000` — feature — Injection contexte portefeuille dans l’opportunity-agent