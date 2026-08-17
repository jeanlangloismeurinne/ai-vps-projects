---
type: audit
audited_file: roadmap-1786358823158-architecture-v2-knowledge-platform.md
audited_title: "Architecture V2 — Knowledge Platform & Flux d'investissement professionnel"
project: portfolio-tracker
created: 2026-08-11
scope: Qualité du flux d'investissement pour un investisseur long terme (+5 ans) & auditabilité du processus
---

# Audit — Flux d'investissement (Architecture V2)

Évaluation du **flux d'investissement** décrit dans `roadmap-1786358823158-architecture-v2-knowledge-platform.md`,
du point de vue d'un **investisseur long terme (+5 ans)**, avec les axes d'amélioration qui préservent — et renforcent — l'**auditabilité**.

---

## Verdict d'ensemble

La spec est solide et intellectuellement honnête : la philosophie curator (MVDD, incertitude bloquante vs investissable,
pile « too hard ») est directement issue de la tradition value/Buffett-Munger et **c'est le meilleur du document**.
L'isolation bull/bear, la traçabilité des sources et le traitement de la mémoire LLM comme source scorée sont d'excellents principes.

Mais le flux souffre de **trois tensions de fond** avec un horizon +5 ans, et **l'auditabilité affichée est plus fragile
qu'elle n'en a l'air** — pas au niveau des intentions, mais au niveau du schéma de données.

---

## 1. Tensions avec l'horizon long terme

### 1.1 Le flux est calibré sur 3 ans, pas 5+
- `bull_case_json` : `horizon_mois: 36`, exit multiple 22x.
- `bear_case.scenario_adverse` : « à 3 ans ».
- Toute la logique de valorisation raisonne en *prix cible* à moyen terme.

Pour un compounder tenu 5-10 ans, le prix cible à 36 mois est presque hors-sujet : ce qui compte est la
**trajectoire de croissance du FCF/action et la durabilité du moat**, pas un multiple de sortie à 3 ans.

**Recommandation** : imposer dans le schéma bull/bear un horizon explicite ≥ 5 ans, avec valorisation *scénarisée*
(bear/base/bull) plutôt qu'un prix cible ponctuel, et un **reverse-DCF** (« qu'est-ce que le prix actuel implique
comme croissance ? ») — outil décisif pour un LT car il révèle les attentes déjà pricées.

### 1.2 La « sortie progressive » est du market-timing déguisé
C'est le point le plus dangereux pour un investisseur LT. Le déclencheur E est :
> Valuation Status 🔴 « Surévalué » = Prix > IV haute × 1.15

Vendre un excellent business parce que le prix dépasse votre estimation d'IV de 15 % est un **anti-pattern documenté
pour la performance long terme** — et la spec le reconnaît, involontairement, dans le post-mortem NVDA :
*« aurais pu garder les tranches 3 et 4 »* et *« seuil de sortie à $150 trop bas »*. Le système est conçu pour produire
exactement l'erreur qu'il regrette ensuite.

Un investisseur LT vend sur **dégradation de la thèse** (moat, ROIC, allocation du capital, gouvernance), pas sur
étirement du prix. L'IV d'un compounder croît dans le temps ; un prix « étiré » aujourd'hui peut être bon marché dans 24 mois.

**Recommandation** :
- Faire de la **dégradation de thèse le déclencheur primaire** de sortie (hypothèse critique invalidée en Mode 2/3/6).
  Le mécanisme existe déjà (E4-1) — il devrait être la voie *normale*, pas l'exception.
- Rétrograder la surévaluation au rang de **signal de non-renforcement et de revue**, pas de vente automatique.
  Si vente il y a, la conditionner à une prime bien plus élevée *et* à une alternative à meilleur rendement attendu
  (coût d'opportunité explicite), pas à un seuil absolu.
- Distinguer nettement dans l'UI **suivi de thèse** (fondamental, moteur des décisions) de **suivi de valorisation**
  (contextuel). Aujourd'hui le thermomètre de prix est trop central et pousse à l'action.

### 1.3 Sur-réaction au bruit trimestriel
Le monitoring modes 1-2 tourne à chaque earnings, recalcule le Valuation Status, rescore les hypothèses. Pour un LT,
le risque est le **churn cognitif** : transformer 20 points de décision annuels là où 2-3 suffisent.

**Recommandation** : hiérarchiser explicitement — Mode 6 (annuel) est la vraie revue de thèse ; les modes trimestriels
ne devraient escalader que sur franchissement de *seuil d'invalidation* pré-enregistré, pas produire un verdict à chaque passage.

---

## 2. Failles d'auditabilité (cœur de l'évaluation)

L'ambition P1-P4 est juste. Mais le schéma DB ne la tient pas encore. Quatre trous concrets :

### 2.1 Les knowledge_entries sont mutables — l'audit pointe vers du sable mouvant
`investment_analyses.knowledge_entry_ids INT[]` référence des entries **par ID**. Or ces entries :
- ont des endpoints `PATCH` et `DELETE`,
- voient leur `reliability_score`, `is_outdated`, `content` évoluer (âge, cross-validation, lint),
- un `INT[]` **n'a aucune intégrité référentielle** (rien n'empêche de supprimer entry_42 alors que 3 analyses la citent).

Conséquence : reconstruire *pourquoi l'agent a dit ce qu'il a dit* (P4) est impossible dès que la base évolue — ce qui
arrive en permanence par design (wiki cumulatif). **C'est la faille structurelle n°1.**

**Recommandation** :
- Rendre les knowledge_entries **append-only + versionnées** (`entry_id`, `version`, `valid_from`, `superseded_by`).
  On ne mute jamais : on crée une nouvelle version et on marque l'ancienne obsolète. `DELETE` devient un soft-delete.
- Remplacer le `INT[]` par une **table de jointure** `analysis_knowledge_refs(analysis_id, entry_id, entry_version,
  content_snapshot, reliability_at_use)` qui **fige l'état exact de la source au moment de la décision**. C'est ce qui
  rend l'audit réellement reconstructible — et c'est peu coûteux.

### 2.2 Pas de vérification que les citations *supportent* l'affirmation (groundedness)
Le principe P2 (mémoire LLM tracée) repose entièrement sur la **bonne foi de l'agent**. Rien ne détecte qu'un agent
présente comme « sourcé sur entry_67 » une affirmation que entry_67 ne soutient pas (citation hallucinée), ni qu'il puise
dans sa mémoire en prétendant citer. Pour un système dont l'argument de vente *est* la traçabilité, c'est un angle mort.

**Recommandation** : ajouter une passe de **vérification de groundedness** (un agent tiers, ou un check LLM-judge peu
coûteux type gemini-flash) qui, pour chaque affirmation du bull/bear, vérifie que les `source_entry_ids` cités contiennent
réellement le fait. Sortie : un `grounding_score` par affirmation + flag des affirmations non étayées. Cela transforme la
traçabilité de *déclarative* en *vérifiée*.

### 2.3 Les overrides utilisateur ne sont pas justifiés/tracés causalement
Q3 conserve `result_json_original` vs `result_json` — bien. Mais l'utilisateur peut faire passer un prix cible de 145 à
200 **sans source ni justification**. Dans un dossier auditable, un override humain qui contredit l'analyse machine est
précisément ce qu'un auditeur veut comprendre.

**Recommandation** : tout champ édité doit exiger une `override_reason` et, idéalement, référencer une knowledge_entry
(créée à cette occasion, `source_type='user_provided'`). Journaliser diff + auteur + timestamp + raison.

### 2.4 Reproductibilité incomplète
provider/model/tokens/cost sont tracés — bien. Mais `temperature: 0.7` rend le résultat non déterministe, et le
**prompt effectif complet** (system + entries injectées + contexte portefeuille) n'est pas stocké. « Reconstruire
pourquoi l'agent a dit ça » exige le *contexte exact*, pas seulement les IDs.

**Recommandation** : persister le **prompt matérialisé complet** (hash + contenu) par analyse. Envisager temperature
basse (0.2-0.3) pour les étapes de synthèse/valorisation où la stabilité prime sur la créativité.

---

## 3. Faiblesses de méthode de décision

### 3.1 Le `confidence_score` global est un faux ami
`confidence = moyenne pondérée des reliability_score des sources`. Cela mesure **la qualité des données**, pas **la
solidité de la thèse** ni **la marge de sécurité**. Afficher « Confiance globale : 72 % » crée une illusion de rigueur
quantitative : deux sources Tier-A impeccables peuvent soutenir un raisonnement fragile. On confond *avoir de bonnes
données* avec *avoir raison*.

**Recommandation** : décomposer en **trois indicateurs distincts, jamais fusionnés** :
1. **Qualité/couverture de l'information** (l'actuel confidence_score + complétude MVDD) ;
2. **Conviction sur la thèse** (jugement, avec justification) ;
3. **Marge de sécurité** (prix vs IV basse).

Un bon investissement LT = les trois élevés. Les mélanger en un seul nombre détruit l'information la plus utile.

### 3.2 Bull et bear partagent le même RAG → adversarialité affaiblie
L'isolation empêche l'ancrage mutuel (bien), mais les deux agents tirent du **même corpus**. Un vrai bear doit *chercher
ce que le bull n'a pas regardé*. Sinon on obtient deux lectures du même dossier, pas une controverse.

**Recommandation** : mandat de recherche **divergent** — le bear doit lancer ses propres `web_search` orientés
falsification (litiges, red flags comptables, avis short-sellers, attrition) et créer ses entries. Ajouter un **round de
réfutation** : le bear voit le bull *après* avoir produit sa thèse indépendante et l'attaque explicitement (une passe,
contexte tracé). La synthèse dialectique vaut mieux qu'une synthèse one-shot.

### 3.3 Aucune calibration des probabilités
Le système produit des probabilités partout (35 %, 45 %, 60 %) mais **rien ne vérifie a posteriori** si les risques
estimés à 40 % se matérialisent ~40 % du temps. Sans boucle de calibration, ces chiffres sont du théâtre de précision.
Or l'infrastructure existe : le **post-mortem** (Phase F) et la `pattern_library`.

**Recommandation** : le post-mortem alimente un **registre de calibration** (risque prédit vs réalisé, IV estimée vs
réalisée). Après 15-20 positions, afficher le biais systématique de l'investisseur (« vos IV hautes sont en moyenne 20 %
trop basses » — exactement la leçon NVDA). C'est le mécanisme d'apprentissage le plus précieux pour un LT, et il boucle
proprement avec l'auditabilité.

### 3.4 Risque non agrégé au niveau portefeuille
Le sizing est par conviction ligne à ligne. Mais deux positions peuvent partager le **même risque de fond** (ex. cycle
CapEx data-center). `MAX_SECTOR_CONCENTRATION_PCT` existe mais n'entre pas dans la Risk Matrix. Pour un LT, la
**corrélation des risques entre holdings** est plus dangereuse que le risque d'une ligne isolée.

**Recommandation** : le thesis-agent, au moment du sizing, reçoit les risques des positions existantes et signale les
**chevauchements de facteurs** (« ce risque “restriction export Chine” pèse déjà sur 22 % du portefeuille »). Tracer
cette exposition agrégée dans la décision.

### 3.5 Résolution de contradictions trop naïve
Le lint résout par « version la plus récente = prédominante ». Faux en finance : un 10-K ancien bat une rumeur de presse
récente.

**Recommandation** : pondérer récence **ET** `reliability_tier`. Un conflit Tier-A vs Tier-C se tranche par le tier ;
deux Tier-A récents se tranchent par la date. Ne jamais auto-résoudre un conflit Tier-A/Tier-A sur un ticker en
portefeuille sans revue humaine.

---

## 4. Points forts à préserver absolument

- **Curator MVDD + readiness + « too hard »** : excellent, ne pas diluer. Seule retouche : le statut `too_complex` doit
  être **révisable** (une entreprise opaque aujourd'hui peut publier demain) — ajouter une date de re-revue plutôt qu'un
  archivage définitif.
- **Mémoire LLM comme source scorée** (P2) : rare et précieux — à renforcer par la vérification de groundedness (§2.2).
- **Pré-mortem obligatoire + acquittement risque par risque** : friction cognitive utile et auditable. Garder.
- **Mode 6 annuel** : c'est *le* bon rythme de revue pour un LT — devrait être promu comme colonne vertébrale du
  monitoring (cf. §1.3).

---

## Synthèse priorisée

| Priorité | Amélioration | Nature |
|---|---|---|
| **P0** | Knowledge_entries versionnées + table de jointure avec snapshot du contenu au moment de la décision | Auditabilité (faille structurelle) |
| **P0** | Requalifier la sortie : dégradation de thèse = déclencheur primaire ; surévaluation ≠ vente auto | Horizon LT |
| **P1** | Vérification de groundedness des citations (agent tiers) | Auditabilité |
| **P1** | Décomposer le confidence_score en 3 (info / conviction / marge de sécurité) | Méthode |
| **P1** | Horizon ≥5 ans + valorisation scénarisée + reverse-DCF | Horizon LT |
| **P2** | Boucle de calibration via post-mortem → pattern_library | Apprentissage |
| **P2** | Mandat de recherche divergent bear + round de réfutation | Qualité analyse |
| **P2** | Overrides utilisateur justifiés et tracés | Auditabilité |
| **P3** | Risque agrégé portefeuille dans le sizing ; résolution de conflits pondérée tier+récence | Robustesse |

**Fil rouge** : l'auditabilité est excellente en intention mais s'appuie sur des données mutables — la rendre
append-only/versionnée (P0) est le geste le plus rentable. Et le flux, tel quel, optimise un horizon 3 ans ; le
réaligner sur 5+ ans se joue surtout sur la logique de sortie, aujourd'hui trop pilotée par le prix.
