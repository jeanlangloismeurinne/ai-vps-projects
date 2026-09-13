---
id: benchmark-methodologies-decision-investissement
status: reference
created: 2026-08-11
project: portfolio-tracker
role: >
  Benchmark des méthodologies professionnelles de décision d'investissement, au niveau du
  processus métier granulaire. Sert à trancher la DÉCISION #1 de la spec V2 (architecture des
  agents d'analyse) et à figer les contrats JSON des agents d'analyse. À lire avec
  00-principe-directeur-v2.md et 01-spec-v2-unifiee.md.
---

# Benchmark — méthodologies de décision d'investissement (processus métier granulaire)

## Objet & méthode

But : rendre **explicite et non ambiguë la logique métier** du flux d'analyse V2, en la fondant
sur les méthodologies réelles des fonds professionnels. On procède en 6 temps :

- **A** — benchmark comparatif des écoles et frameworks (ce qu'ils optimisent, ce qu'ils produisent).
- **B** — le **processus métier canonique granulaire** (15 étapes), chacune avec objectif / inputs / méthode / **artefact de sortie** / **gate de décision**.
- **C** — ce que le benchmark tranche pour la **DÉCISION #1** (recherche collaborative vs interprétation adversariale).
- **D** — les **contrats JSON** des agents d'analyse, dérivés du benchmark.
- **E** — matrice de traçabilité *méthodologie → étape → champ JSON*.
- **F** — questions ouvertes restant à trancher.

Principe directeur applicable : la logique de décision (le processus ci-dessous) **précède et contraint**
l'UX et le schéma JSON ; les JSON encodent la méthodologie de façon que l'agent **ne puisse pas
sauter une étape** (G1/G2 de la constitution).

---

## Partie A — Benchmark comparatif

### A1. Écoles d'analyse fondamentale

| École | Représentants | Ce qu'elle optimise | Sortie caractéristique | Ce qu'on en retient pour le système |
|---|---|---|---|---|
| **Deep value / net-net** | Graham, Schloss | Décote sur actifs tangibles, marge de sécurité quantitative | Valeur liquidative vs prix | Marge de sécurité comme *plancher*, pas comme thèse ; peu applicable aux compounders |
| **Quality-at-fair-price** | Buffett/Munger, Fundsmith (T. Smith) | Qualité durable du business × prix raisonnable | Thèse « wonderful business + moat + prix correct » | **Séparer qualité et prix** en deux axes ; ROIC/FCF au centre ; « too hard pile » |
| **Quality-growth** | Baillie Gifford, T. Rowe | Croissance durable réinvestie à haut ROIC | Runway de réinvestissement, TAM, optionalité | Champ « reinvestment runway » + optionalité comme driver de valeur LT |
| **Scale economics shared** | Nomad (Sleep/Zakaria) | Avantage de coût redistribué au client → boucle vertueuse | Modèle de la boucle (coût↓→volume↑→coût↓) | Type de moat « scale economics shared » à typer explicitement |
| **Franchise / EPV** | B. Greenwald | Séparer valeur d'actif, valeur de rentabilité (EPV), valeur de croissance | Asset value → EPV → growth value ; croissance ne vaut que sous moat | **Décomposer la valorisation** : ne valoriser la croissance que si moat confirmé |
| **Special situations** | Greenblatt, spinoffs | Mispricing structurel (forced sellers, complexité) | Catalyseur + calendrier | Champ « pourquoi mispricé » = structurel vs analytique |
| **Long/short — variant perception** | hedge funds fondamentaux | Écart entre consensus et réalité + catalyseur | « Variant perception » explicite + trigger de re-rating | Impose le champ **edge / pourquoi le marché se trompe** |

**Convergence clé** : toutes ces écoles, sauf la deep value pure, décomposent la décision en
**(1) qualité du business** · **(2) qualité financière** · **(3) management/allocation du capital** ·
**(4) valorisation/marge de sécurité** · **(5) raison du mispricing**. C'est le squelette du memo.

### A2. Frameworks de valorisation

| Framework | Auteur | Principe | Sortie | Rôle dans le système |
|---|---|---|---|---|
| **DCF intrinsèque scénarisé** | Damodaran | Actualiser les FCF futurs sous hypothèses explicites | Fourchette IV (bear/base/bull) + drivers | Valorisation primaire, **scénarisée** (jamais un point) |
| **EPV + valeur de croissance** | Greenwald | Valeur de rentabilité normalisée sans croissance, puis prime de croissance conditionnée au moat | EPV, écart EPV/prix | Contrôle de cohérence : la croissance payée est-elle justifiée par le moat ? |
| **Expectations investing / reverse-DCF** | Mauboussin/Rappaport | Inverser le DCF : *quelles* hypothèses le prix actuel implique-t-il ? | Croissance/marge implicites au prix | **Champ obligatoire** : ce que le marché price déjà (anti-ancrage) |
| **Multiples normalisés / relatifs** | pratique buy-side | Comparer à l'historique et aux pairs sur métriques normalisées | Multiple vs historique/pairs | Triangulation, jamais seul |
| **Base rates / outside view** | Kahneman, Mauboussin (*Base Rates*) | Ancrer les prévisions sur une classe de référence, pas sur le narratif | Taux de base (ex. % d'entreprises maintenant >20% de croissance 10 ans) | **Champ obligatoire** : ancre de base-rate sous chaque prévision clé |

**Convergence clé** : une valorisation crédible = **plusieurs lentilles** (intrinsèque scénarisée +
reverse-DCF + relatif) **+ ancrage base-rate**. Un prix cible unique est un anti-pattern.

### A3. Qualité de décision & maîtrise des biais

| Framework | Auteur | Apport | Traduction système |
|---|---|---|---|
| **Process > outcome** | Mauboussin, A. Duke (*Thinking in Bets*) | Juger la *qualité de la décision* indépendamment du résultat | Figer le raisonnement + preuves au moment T (snapshots, auditabilité) ; calibrer après coup |
| **Falsifiabilité / invert** | Popper, Munger | Une thèse = des affirmations réfutables ; « invert, always invert » | Hypothèses avec **seuils d'invalidation** chiffrés |
| **Pre-mortem** | G. Klein | « Supposez l'échec dans 3 ans — pourquoi ? » avant de décider | Bloc pré-mortem obligatoire, acquitté |
| **Steelman adverse** | Munger (« je dois défendre la position adverse mieux que ses partisans ») | Construire le meilleur cas *contre* | Bear-agent à **recherche divergente** + round de réfutation |
| **Second-level thinking / cycles** | H. Marks | Ne pas confondre « bonne entreprise » et « bon investissement » ; où en est le cycle | Séparer qualité (business) et attractivité (prix × cycle) ; température de marché |
| **Calibration probabiliste** | Tetlock (*Superforecasting*) | Prévisions comme probabilités, scorées a posteriori ; mise à jour bayésienne | Probabilités partout + **registre de calibration** (prédit vs réalisé) |
| **Decision journal** | Kahneman, Tren Griffin | Consigner la décision et son contexte pour combattre l'hindsight bias | `result_json_original` + prompt figé + post-mortem |

**Convergence clé** : la qualité de décision se construit **avant** de connaître le résultat, par
falsifiabilité + adversarialité + probabilités calibrées + journalisation. Ces quatre exigences
doivent être **matérialisées dans les JSON**, sinon elles n'existent pas.

### A4. Processus institutionnels (comment un fonds structure réellement la décision)

| Processus | Origine | Étapes saillantes | Ce qu'on en retient |
|---|---|---|---|
| **Comité d'investissement (IC) PE/VC** | private equity | Analyste champion rédige un memo → IC challenge (avocat du diable) → vote sous conditions | **Séparation des rôles** : un producteur de thèse, un challenger, un décideur |
| **Checklist investing** | Pabrai/Spier (inspiré Gawande) | Checklist des causes d'échec passées, passée avant décision | Checklist MVDD + causes d'échec récurrentes (pattern library) |
| **Scuttlebutt** | P. Fisher | Recherche qualitative primaire (clients, ex-employés, concurrents) | Recherche ad hoc tracée (`search-worker`) au-delà des chiffres |
| **Dialectical inquiry / devil's advocate** | théorie de la décision (Mason & Mitroff) | Thèse et contre-thèse explicites, puis synthèse | Fonde le bull/bear ; mais *après* une base factuelle commune |
| **Kill-the-company / red team** | management stratégique | Exercice dédié « comment tuer cette entreprise » | Alimente pré-mortem + bear |

**Convergence clé** : dans un vrai fonds, la **collecte de faits** (recherche) et la **contestation
du jugement** (IC/red-team) sont **deux phases distinctes**, avec des **rôles séparés**. C'est le
point décisif pour la DÉCISION #1 (voir Partie C).

---

## Partie B — Processus métier canonique (granulaire)

Synthèse des benchmarks en un flux à 15 étapes. Chaque étape : **objectif · inputs · méthode ·
artefact de sortie · gate**. Les étapes 1-2 relèvent de la couche données/curator ; 3-12 sont le
cœur analytique (agents d'analyse) ; 13-15 le suivi/apprentissage.

| # | Étape | Objectif | Méthode / benchmark | Artefact de sortie | Gate |
|---|---|---|---|---|---|
| 1 | **Sourcing** | Générer l'idée | screens, thèmes, spinoffs, insider buying, low-expectation | `ticker` + note d'origine | — |
| 2 | **Triage / quick-kill** | Éliminer vite | cercle de compétence · qualité & solvabilité rapides · zone de valo · « raison d'un mispricing ? » | `readiness_report` (GO/NO-GO) | **GO** requis. Incertitude = signal d'arrêt (too-hard) |
| 3 | **Modèle économique** | Comprendre comment l'argent est gagné | unit economics, récurrence, proposition de valeur | bloc `business_model` | — |
| 4 | **Moat** | Défendabilité à 5-10 ans | typologie (intangibles, switching costs, network, coût, échelle) · **tendance** du moat | bloc `moat` (type, score, durabilité, **trend**) | — |
| 5 | **Qualité financière** | Rentabilité réelle & soutenable | ROIC vs WACC & tendance · conversion FCF · intensité capitalistique · **qualité des résultats** (accruals) · levier | bloc `financials` | Flag si earnings quality faible |
| 6 | **Management & allocation du capital** | Juger les décideurs | grille *Outsiders* (Thorndike) : M&A, buybacks *au bon prix*, dividendes, réinvestissement · incitations · skin-in-the-game · candeur | bloc `management` (scorecard allocation) | — |
| 7 | **Secteur & concurrence** | Position dans la structure | 5 forces (Porter), croissance, cyclicité, disruption, position vs pairs | bloc `industry` | — |
| 8 | **Valorisation multi-lentilles** | Estimer l'IV et la marge de sécurité | DCF scénarisé (Damodaran) + EPV (Greenwald) + **reverse-DCF** (Mauboussin) + relatif + **base-rate** | bloc `valuation` (fourchette + implicite + ancre) | — |
| 9 | **Edge / pourquoi mispricé** | Articuler l'avantage | informationnel / analytique / temporel (Marks) + catalyseur de re-rating | bloc `variant_perception` | **Pas d'edge articulé = pas de thèse** |
| 10 | **Thèse falsifiable** | Poser ce qui doit être vrai | 3-5 hypothèses réfutables + KPI + **seuils d'invalidation** + horizon ≥5 ans | `thesis.hypotheses[]` | — |
| 11 | **Contestation (bull/bear + pré-mortem)** | Attaquer le jugement | steelman adverse (Munger) · pré-mortem (Klein) · kill-the-company · **résoudre les 2-3 incertitudes bloquantes** | `bull_case`, `bear_case`, `pre_mortem` | Incertitude bloquante non résolue = pause |
| 12 | **Décision / IC** | Trancher & dimensionner | synthèse dialectique · sizing (conviction × marge de sécurité × corrélation, cap) · coût d'opportunité · conditions d'entrée · **acquittement des risques** | `risk_matrix` + sizing | Tous risques + pré-mortem acquittés |
| 13 | **Monitoring** | Suivre la thèse | suivi des hypothèses/KPI vs seuils · revue annuelle (mode 6) | `monitoring_json` par mode | Escalade si seuil franchi |
| 14 | **Sortie** | Discipline de vente | thèse rompue · **thèse ne justifie plus le prix** (rendement prospectif) · meilleure opportunité | `exit_plan` | — |
| 15 | **Post-mortem & calibration** | Apprendre | process>outcome · prédit vs réalisé · pattern library | `post_mortem` + `calibration` | — |

> **Lecture** : les étapes 3-8 sont **fact-finding + analyse neutre** (une seule version des faits,
> cumulative — le wiki). Les étapes 9-12 sont **jugement contestable** (edge, thèse, bull/bear,
> décision). Cette frontière est le cœur de la DÉCISION #1.

---

## Partie C — Ce que le benchmark tranche pour la DÉCISION #1

**Question** : les deux specs V2 proposaient soit un entonnoir séquentiel (screening→research→thèse),
soit une analyse adversariale (bull ∥ bear → synthèse). Le benchmark montre que **ce ne sont pas des
rivaux mais deux phases d'un même processus** : la recherche est un entonnoir, la décision est une
contestation. La vraie question de design est : **où placer la frontière fact-finding / jugement, et
qui porte l'adversarialité.**

Les processus d'IC professionnels donnent une réponse nette : **on ne rend pas la collecte des faits
adversariale** (on veut *une* base factuelle exacte et partagée), **on rend le jugement adversarial**
(un champion, un challenger, un décideur). D'où trois options concrètes pour nos agents :

| Option | Description | Force | Faiblesse | Fidélité au benchmark |
|---|---|---|---|---|
| **A — Séquentiel + red-team** | `research-agent` produit un memo neutre complet (3-9) ; un `challenger-agent` l'attaque ; `synthesis` tranche | Simple, économe, colle à l'IC réel (analyste + challenger) | Le memo « neutre » peut être biaisé par un seul auteur | Élevée (modèle IC classique) |
| **B — Adversarial symétrique** | `bull` et `bear` construisent chacun leur cas **de zéro, isolés**, depuis la même base | Anti-ancrage maximal | Coûteux ; deux « navires qui se croisent » ; duplication du fact-finding | Moyenne (débat structuré, mais fact-finding dédoublé) |
| **C — Base commune + jugement adversarial** ✅ | `research-agent` construit la **base factuelle neutre versionnée** (3-8) ; **puis** `bull` et `bear` argumentent depuis cette base (recherche *divergente* autorisée sur les zones de désaccord) ; `synthesis` réconcilie | Sépare faits (cumulatifs, audités) et jugement (contesté) ; anti-ancrage sans dédoubler la collecte ; auditable | Un peu plus d'étapes | **La plus élevée** — reproduit exactement fact-finding collaboratif + IC adversarial |

**Recommandation : Option C.** Elle est la traduction directe de la convergence A4 (« collecte des
faits ≠ contestation du jugement, rôles séparés »), elle satisfait l'audit (bear à recherche
divergente + round de réfutation ; base de connaissance versionnée partagée), et elle respecte le
principe directeur (fact-finding = couche données cumulative ; jugement = couche agents contestée).

**Ce que C implique concrètement** :
1. `research-agent` produit un `research_memo` **neutre** (business/moat/financials/management/industry/valuation) — pas de recommandation d'achat, juste les faits analysés et les **incertitudes bloquantes** identifiées.
2. Le curator (readiness) a déjà filtré et garantit la suffisance d'information (arrêt de Pareto).
3. `bull-agent` et `bear-agent` reçoivent le **même** `research_memo` + la même base `knowledge_entries` ; chacun peut lancer une **recherche divergente** ciblée sur les points de désaccord (bear orienté falsification) ; contexte isolé l'un de l'autre.
4. Round de réfutation : le bear voit le bull et l'attaque (une passe).
5. `synthesis` (thesis-agent) produit `risk_matrix` + pré-mortem + sizing + thèse falsifiable.

> **À trancher réellement (Partie F)** : (a) Option C confirmée ? (b) le research_memo est-il neutre
> ou porte-t-il déjà une pré-recommandation ? (c) bull/bear isolés stricts, ou bear voit le memo *et*
> le bull d'emblée ? (d) une passe de réfutation ou un mini-débat multi-tours ?

---

## Partie D — Contrats JSON des agents d'analyse (dérivés du benchmark)

Principe : chaque JSON **encode la méthodologie** — champs obligatoires qui forcent l'étape, et
`source_entry_refs` (grounding A2) sur toute affirmation factuelle. Ci-dessous les *incréments* par
rapport aux schémas déjà dans `01-spec-v2-unifiee.md` (on ne réécrit pas l'existant, on le complète).

### D1. `research_memo_json` (agent research — base neutre, étapes 3-8)

```json
{
  "business_model": {"description":"...","drivers_revenus":[],"recurrence_pct":90,
                     "unit_economics":"...","source_entry_refs":[{"entry_id":12,"version":1}]},
  "moat": {"type":["switching_costs","scale_economics_shared"],"score":4,
           "durabilite_ans":{"forte":5,"incertaine":10},
           "trend":"widening|stable|eroding","preuves":[{"fait":"...","source_entry_refs":[]}]},
  "financials": {"roic_pct":18,"wacc_estime_pct":9,"roic_vs_wacc":"spread positif durable",
                 "roic_trend_5y":"stable","fcf_conversion_pct":85,"intensite_capex_pct":6,
                 "earnings_quality":{"score":"high","accruals_flag":false,"note":"..."},
                 "levier":{"dette_nette_ebitda":-0.3},"source_entry_refs":[]},
  "management": {"capital_allocation_scorecard":{
                    "ma":"disciplinée","buybacks":"opportunistes sous IV","dividendes":"modérés",
                    "reinvestissement":"fort ROIC","note":"grille Outsiders"},
                 "incitations":"...","skin_in_game_pct":1.6,"candeur":"...","score":3},
  "industry": {"structure_5forces":"...","croissance_marche_pct":12,"cyclicite":"faible",
               "disruption_vectors":[],"position_vs_pairs":"leader mid-market"},
  "valuation": {
     "dcf_scenarios":{"bear":95,"base":130,"bull":165,"drivers":{"croissance":0.10,"marge_fcf":0.28}},
     "epv":{"valeur_rentabilite":105,"note":"croissance payée justifiée par moat: oui/non"},
     "reverse_dcf":{"croissance_implicite_prix_actuel_pct":14,
                    "verdict":"le prix price une croissance > à notre base"},
     "relatif":{"multiple":"EV/FCF 22x","vs_historique":"prime 15%","vs_pairs":"en ligne"},
     "base_rate_anchor":{"reference_class":"SaaS >1Md$ maintenant >12% croissance 10 ans",
                         "taux_base_pct":15,"note":"notre base suppose le quartile favorable"},
     "prix_actuel":108,"iv_range":[95,140],"marge_securite_base_pct":-6
  },
  "incertitudes_bloquantes":[{"question":"...","impact_si_non_resolu":"inverse la thèse",
                              "statut":"resolue|en_cours|non_resolvable","source_entry_refs":[]}],
  "incertitudes_investissables":[{"question":"...","fourchette":"n'inverse pas la décision"}],
  "posture":"NEUTRE — pas de recommandation ; base factuelle pour bull/bear"
}
```

### D2. `bull_case_json` / `bear_case_json` (étape 11 — jugement adversarial)

Incréments par rapport à la spec : **variant perception** (edge), **base-rate** sous chaque prévision,
**recherche divergente** tracée, **probabilités**.

```json
{
  "variant_perception": {"type":"analytique|informationnel|temporel",
     "enonce":"le marché sous-estime la durabilité du moat car ...",
     "catalyseur_re_rating":"...","horizon_mois":36,"source_entry_refs":[]},
  "arguments":[{"titre":"...","explication":"...","probabilite":0.6,
                "base_rate":{"reference_class":"...","taux":0.4,"ajustement":"+ car ..."},
                "source_entry_refs":[{"entry_id":42,"version":3}],
                "recherche_divergente":[{"query":"...","finding_entry_id":91}]}],
  "valorisation_cote": {"horizon_ans":5,"scenarios":{"bear":..,"base":..,"bull":..},
                        "reverse_dcf_commentaire":"..."},
  "conviction": 7,
  "indicateurs": {"qualite_info":0.74,"conviction":0.70,"marge_securite":0.20},
  "grounding_report": {"affirmations_total":9,"etayees":9,"non_etayees":0}
}
```
Le `bear_case_json` ajoute `failles_bull_conventionnel[]`, `scenario_destruction_valeur{}` et, après
le round de réfutation, `refutation_du_bull[]` (attaque explicite des arguments bull).

### D3. `risk_matrix_json` (étape 12 — synthèse/IC)

Incréments : **quatre axes séparés** (pas de score fusionné), **base-rate du verdict**, **sizing**
avec corrélation portefeuille, **thèse falsifiable** liée.

```json
{
  "verdict":"PROCEED|PROCEED_AVEC_CONDITIONS|PASSER|SURVEILLER|TOO_HARD",
  "rationale":"...",
  "axes":{"qualite_business":0.8,"qualite_info":0.72,"conviction":0.71,"marge_securite":0.15},
  "risques_acceptes":[{"risque":"...","probabilite":0.35,"impact":"fort","reversible":false,
     "base_rate":{"reference_class":"...","taux":0.3},
     "reponse_si_materialise":"réduire si perte PDM > 3pts / 2 trimestres",
     "hypothese_liee":"H3","source_entry_refs":[]}],
  "pre_mortem":["échec 1 ...","échec 2 ...","échec 3 ..."],
  "position_sizing":{"pct_recommande":4.5,"pct_max":7.0,"methode":"conviction × MoS × (1/corrélation), cappé",
     "risques_correles_portefeuille":[{"facteur":"CapEx datacenter","exposition_pct":22}],
     "cout_opportunite":"vs meilleure alternative en portefeuille: ..."},
  "conditions_entree":["prix < 115 pour MoS > 10%"],
  "sources_summary":{"tier_A":12,"tier_B":8,"tier_C_llm_memory":3}
}
```

### D4. `thesis_json.hypotheses[]` (étape 10 — falsifiabilité)

```json
{"id":"H3","enonce":"NVDA conserve >80% de PDM GPU IA jusqu'en 2028",
 "kpi":"part de marché GPU datacenter","unite":"%",
 "seuil_alerte":78,"seuil_invalidation":72,"horizon":"2028",
 "base_rate":{"reference_class":"leaders tech maintenant >80% PDM 4 ans","taux":0.45},
 "statut":"active","source_entry_refs":[]}
```

**Règles transverses aux quatre contrats** (issues du benchmark) :
1. Toute affirmation factuelle porte `source_entry_refs` (grounding vérifié — A2).
2. Toute prévision porte une **ancre base-rate** (A2/A3) — interdiction du point sans référence.
3. Les hypothèses portent un **seuil d'invalidation chiffré** (falsifiabilité — A3).
4. Les axes qualité/info/conviction/marge de sécurité restent **séparés** (Buffett/Marks — jamais un score unique).
5. La valorisation porte **toujours** le reverse-DCF (ce que le prix price — Mauboussin).
6. Le champ **variant perception** est obligatoire : pas d'edge articulé ⇒ pas de thèse (Marks/long-short).

---

## Partie E — Matrice de traçabilité (méthodologie → étape → champ JSON)

| Méthodologie | Étape B | Champ(s) JSON qui la matérialisent |
|---|---|---|
| Quality-at-fair-price (Buffett) | 3-5, 8 | `business_model`, `moat`, `financials`, `valuation` séparés |
| Moat + tendance (Morningstar/Porter) | 4 | `moat.type`, `moat.trend`, `moat.durabilite_ans` |
| ROIC vs WACC & qualité résultats (Greenwald) | 5 | `financials.roic_vs_wacc`, `financials.earnings_quality` |
| Outsiders / capital allocation (Thorndike) | 6 | `management.capital_allocation_scorecard` |
| DCF scénarisé (Damodaran) | 8 | `valuation.dcf_scenarios` |
| EPV / croissance conditionnée au moat (Greenwald) | 8 | `valuation.epv` |
| Reverse-DCF / expectations (Mauboussin) | 8 | `valuation.reverse_dcf` |
| Base rates / outside view (Kahneman/Tetlock) | 8, 11 | `base_rate_anchor`, `base_rate` sur arguments/risques/hypothèses |
| Variant perception / edge (Marks) | 9 | `variant_perception` |
| Falsifiabilité / invert (Popper/Munger) | 10 | `hypotheses[].seuil_invalidation` |
| Steelman adverse (Munger) | 11 | `bear_case` + `refutation_du_bull` |
| Pre-mortem (Klein) | 11-12 | `pre_mortem[]` |
| Sizing conviction × MoS × corrélation (Kelly capé) | 12 | `position_sizing` |
| Coût d'opportunité (portefeuille) | 12 | `position_sizing.cout_opportunite`, `risques_correles_portefeuille` |
| Discipline de sortie thèse-vs-prix | 14 | `exit_plan` (réévaluation rendement prospectif) |
| Process > outcome + calibration (Duke/Tetlock) | 15 | `post_mortem`, `calibration_registry`, prompt figé |

Lecture inverse utile pour l'agent aval : **aucun champ du benchmark ne doit disparaître au découpage
en tickets.** Un ticket d'agent d'analyse est incomplet si son contrat JSON n'implémente pas les
6 règles transverses (Partie D).

---

## Partie F — Questions ouvertes pour trancher la DÉCISION #1

1. **Option C confirmée** (base neutre → bull/bear → synthèse) ? Sinon A (analyste+challenger) ou B (symétrique) ?
2. **Neutralité du research_memo** : purement factuel, ou porte-t-il déjà un `verdict_recherche` (PROCEED/PASSER) comme dans la spec *Processus fonds* ? *(Reco : neutre — le verdict naît de la synthèse, pas de la recherche, pour ne pas ancrer bull/bear.)*
3. **Isolation bull/bear** : stricte (aucun ne voit le memo pré-annoté ni l'autre), ou bull et bear voient le memo neutre mais pas le cas adverse jusqu'au round de réfutation ? *(Reco : memo commun, cas adverse caché jusqu'à la réfutation.)*
4. **Profondeur de contestation** : une passe de réfutation (bear→bull), ou un mini-débat multi-tours arbitré par la synthèse ? *(Reco : une passe — coût/valeur ; multi-tours réservé aux `conviction < seuil`.)*
5. **Rôle du curator vs research** : le curator (readiness) tranche le GO/NO-GO *avant* la recherche approfondie ; le research ne démarre que sur GO. Confirmé ?
6. **Sizing** : formule explicite (conviction × MoS × 1/corrélation, cappée par `MAX_SECTOR_CONCENTRATION`) ou fourchette libre justifiée par l'agent ? *(Reco : formule comme point de départ, ajustable avec justification tracée.)*

Une fois #1 tranchée sur la base de ce benchmark, on fige les contrats JSON (Partie D) dans la spec
unifiée (§8) et on lève le verrou du lot 6 pour l'agent de génération de tickets.
