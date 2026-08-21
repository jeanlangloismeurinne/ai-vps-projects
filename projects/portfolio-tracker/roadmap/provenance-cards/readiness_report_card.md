---
id: readiness-report-card
status: carte-de-provenance
created: 2026-08-20
project: portfolio-tracker
role: >
  Carte de provenance champ-par-champ du `readiness_report_json` (curator, §7) — le GO/NO-GO du
  flux (ex-screening). 5ᵉ et dernier contrat majeur du chemin critique. Complète la couche contrat :
  research_memo · bull/bear · risk_matrix · hypotheses[] (analysis_v2_schemas.py) + readiness (ici).
  Pydantic : readiness_report_schema.py. Dérivation : readiness_derivation.md. Voir §7 de
  01-spec-v2-unifiee.md.
---

# Carte de provenance — `readiness_report_json` (curator)

## Ce qui distingue cette carte des 4 autres

Les 4 JSON d'analyse sont produits **par des agents** (jugement + délégation) : leur carte mêle
`factual` / `judgment` / `derived`. Le `readiness_report` est **produit par le curator comme
projection déterministe de l'état de la KB** — presque tous ses champs sont `derived` **à formule
connue**, donc **recomputables sans token LLM**. C'est ce qui en fait le gate *bon marché* placé
**avant** toute dépense Opus (constitution §3 : déterministe d'abord).

Il n'est pas *grounded sur des refs* comme un fait d'analyse : il est **grounded sur l'existence
d'entries** (∃ `knowledge_entry` couvrant chaque champ factual au tier ≥ plancher). Sa vérification
est donc la même que la colonne « Gap si non-fondable » des cartes du `research_memo`, exécutée en
amont plutôt qu'en aval.

## Twin table — validation (A) & provisioning/traçabilité (B)

| Champ | nature | grounding | Vérification (A2) | Provisioning (d'où vient la valeur) |
|---|---|---|---|---|
| `verdict` | **derived** | hérité (coverage) | **recompute déterministe** = `compute_verdict(coverage)` (§7) ; `too_hard`/`researching` exclus (décision/état) | fonction des `bloc_ok` des 2 blocs |
| `coverage.structuree.dimensions[].ok` | **derived** | hérité (existence) | déterministe : `ok ⇔ champs_non_fondables = ∅` | ∃ entry couvrant chaque champ factual, tier ≥ plancher |
| `coverage.*.dimensions[].tier_atteint` | **derived** | hérité | max tier des entries couvrantes (None si non couvert) | KB : meilleur `reliability_tier` couvrant |
| `coverage.*.dimensions[].champs_non_fondables[]` | **derived** | hérité | sous-ensemble de `champs_requis` (Pydantic) | champs factuels sans entry fondante |
| `coverage.*.bloc_ok` | **derived** | hérité | déterministe : `∧ dimensions.ok` | agrégat du bloc |
| `entries_par_tier` | **derived** | hérité | recompute des comptes (comme `sources_summary`) : somme = total | `COUNT(*) GROUP BY reliability_tier` sur la KB du ticker |
| `indicateurs.qualite_info` | **derived** | hérité | cohérence couverture × tiers (LLM-judge léger optionnel) | couverture pondérée par tiers |
| `indicateurs.conviction` · `marge_securite` | **contrôle** | — | **None au readiness** (A3 : jamais fusionnés ; formés par l'analyse aval) | pending — produits par bull/bear/synthèse |
| `incertitudes_bloquantes[]` | **judgment** | délégué (entries `risk`) | LLM-judge léger : cohérence avec les entries risque | identifiées par le curator |
| `incertitudes_investissables[]` | **judgment** | — | non bloquant (n'inverse pas la décision) | curator |
| `gaps[]` | **derived** | hérité (non-fondables) | déterministe : **bijection stricte** `⋃ gaps[dim].champs_cibles == champs_non_fondables[dim]` (option B) ; schéma unique curator \| gap-intake (§7) | émis pour chaque champ factual non fondable |
| `gaps[].champs_cibles[]` | **ref** | — | ⊆ `champs_non_fondables` de la dimension (pas de gap fantôme) ; jamais vide | les champs manquants que ce gap comble (grain champ) |
| `gaps[].origine` | **contrôle** | — | `Literal[curator, gap_intake]` — les 2 sources, 1 pipeline | curator (auto) ou gap-intake (NL utilisateur) |
| `arret_pareto_recommande` | **judgment** | — | recommandation curator (impact marginal faible) — **non contraignant** (utilisateur garde l'override) | curator |
| `context_pack_entry_id` | **ref** | — | `entry_id ∈ KB`, `source_type='agent_synthesis'` ; **obligatoire si `ready`** | artefact distillé réutilisable (§7, front-load aval) |
| `rationale` | **judgment** | — | texte non vide | curator |

## Garde-fous encodés (readiness_report_schema.py)

- **G2 — le verdict est contraint, pas libre.** `_verdict_contraint` recompute le verdict depuis la
  coverage : un dossier **structuré-complet mais mince en qualitatif** sort **`thin_qualitative`,
  jamais `ready`** (anti-faux-complet, prouvé sur NVDA). `too_hard` (décision A10) et `researching`
  (état transitoire de la boucle) sont les deux seuls verdicts non dérivés de la coverage.
- **Gate d'explicabilité (option B — au grain champ).** **Aucun champ non fondable ne peut rester
  silencieux** : bijection stricte `champs_non_fondables ↔ gaps[].champs_cibles` par dimension
  (couverture complète **et** pas de gap fantôme sur un champ déjà fondable). L'arrêt de Pareto se
  module par `priorite` / `arret_pareto_recommande`, **jamais** en retirant un gap. Seul `too_hard`
  est exempté : le blocage y est une décision (A10), pas un manque comblable par recherche — il
  s'exprime en `incertitudes_bloquantes[non_resolvable]`, pas en gap actionnable.
- **`ok` / `bloc_ok` dérivés.** Impossible de déclarer `ok=True` avec un champ non fondable, ni un
  `bloc_ok` incohérent avec ses dimensions — la déclaration est refusée à la construction.
- **A3.** `conviction` / `marge_securite` restent `None` au readiness : aucun score de confiance
  global ne peut naître à ce stade.
- **`ready` ⇒ `context_pack_entry_id`.** Le verdict GO exige l'artefact distillé front-loadé
  (réutilisation research/bull/bear + cache, §5.3) — les tokens de l'assessment ne sont pas perdus.

## Boucle d'approfondissement (§7) — les gaps pilotent le search-worker

```
readiness --NO-GO--> gaps[] (dispatchables) --user choisit--> search-worker (Haiku, tier ouvrier)
    ^                                                                  |
    |                                store_knowledge (entries scorées) |
    +------------------------------- re-run readiness -----------------+
```

Toute la boucle est en **tier ouvrier, avant tout appel Opus**. L'arrêt de Pareto est la
*recommandation* du curator ; le **plancher qualitatif interdit** de s'arrêter avant décidabilité ;
l'utilisateur garde l'**override** tracé (aller un tour plus loin).

## Stockage — `knowledge_curator_reports` (migration 024, déjà appliquée)

| Colonne table | Source dans le JSON |
|---|---|
| `report_type` | `'readiness'` (CHECK : mvdd \| readiness \| lint) |
| `report_json` | le `readiness_report_json` complet (contrat versionné ci-dessus) |
| `verdict` | `readiness_report_json.verdict` (dénormalisé pour l'index/badge watchlist) |
| `coverage_structuree` | `coverage.structuree` |
| `coverage_qualitative` | `coverage.qualitative_marche` |
| `context_pack_entry_id` | `context_pack_entry_id` (FK `knowledge_entries`) |

Pas de nouvelle migration : la table couvre déjà mvdd + readiness + lint (fusion screening→curator, §7).

## Les 3 points de synchronisation (G1, règle #19)

1. **Prompt curator** (mode Readiness) — le schéma de sortie attendu = ce contrat.
2. **Frontend** — page Readiness : 2 barres de couverture struct/qual, badge verdict, liste `gaps[]`
   (bouton « approfondir »), champ gap en langage naturel ; bouton « Analyser » actif **ssi `ready`**.
3. **Import / validation backend** — `ReadinessReport` (Pydantic) à l'écriture dans
   `knowledge_curator_reports.report_json`.

## Ancrage

- Pydantic vérifié (pydantic 2.13.4, container backend) : `readiness_report_schema.py` — cas NVDA
  réel → `thin_qualitative`, G2 rejette un `ready` forcé.
- Dérivation coverage → verdict : `readiness_derivation.md`.
- Vérification par nature : `groundedness_rules.md`. Curator / gaps / thin_qualitative : §7.
- Contrats d'analyse (les 4 autres cartes) : `analysis_v2_schemas.py` + §8.
