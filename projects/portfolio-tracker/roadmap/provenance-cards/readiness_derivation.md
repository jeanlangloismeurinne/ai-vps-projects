---
id: readiness-derivation
status: derivation
created: 2026-08-19
project: portfolio-tracker
role: >
  Dérivation de la checklist de couverture du curator (readiness) à partir des cartes de
  provenance des 4 JSON d'analyse. Garantie (3) « agent provisionné » : a-t-on de quoi
  remplir chaque champ factual au moment de l'analyse ? Voir analysis_v2_schemas.py (Pydantic)
  et §7 de 01-spec-v2-unifiee.md.
---

# Readiness ← champs factuels (dérivation)

## Principe

La readiness **n'est pas** un contrôle séparé : c'est la **projection des cartes de provenance
du `research_memo`** sur `(dimension MVDD → champs factual → tier plancher)`.

- Seuls les champs de **nature `factual`** (et les `preuves[]` sur lesquelles s'adosse un `judgment`)
  créent une exigence de couverture. Les `judgment` / `derived` sont **produits à l'analyse**,
  pas pré-collectés.
- Une dimension MVDD atteint son **plancher** ⇔ **chacun de ses champs factuels est fondable**
  = il existe ≥1 `knowledge_entry` qui le couvre, au `reliability_tier` ≥ plancher.
- C'est **calculable avant la recherche approfondie** : il suffit de vérifier l'*existence* d'entrées
  fondantes — exactement la colonne « Gap si non-fondable » des cartes.

## Règle de verdict (curator, §7)

```
dimension_ok(d)      := ∀ champ factual f ∈ d,  ∃ entry couvrant f  avec tier(entry) ≥ plancher(f)
structuree_ok        := dimension_ok(business_model) ∧ dimension_ok(financials) ∧ dimension_ok(valorisation)
qualitative_ok       := dimension_ok(produits) ∧ dimension_ok(positionnement)
                         ∧ dimension_ok(marché) ∧ dimension_ok(management) ∧ dimension_ok(risques)

ready            ⇔ structuree_ok ∧ qualitative_ok
thin_qualitative ⇔ structuree_ok ∧ ¬qualitative_ok          # complet sur les chiffres, mince ailleurs
not_ready        ⇔ ¬structuree_ok
```

Chaque champ factual non fondable émet un `gaps[] = {dimension, manque, queries_suggerees,
priorite, coverage_actuelle}` → boucle d'approfondissement Q5 (search-worker) → re-run readiness.

## Matrice de dérivation

| Bloc | Dimension MVDD | Champs factuels requis fondables | Tier plancher | Gap émis si manquant |
|---|---|---|---|---|
| **structurée** | business model | `business_model.description` · `drivers_revenus` · `recurrence_pct` | B+ / A | modèle économique non documenté |
| structurée | ≥3 ans financials | `financials.roic_pct` · `fcf_conversion_pct` · `intensite_capex_pct` · `levier.dette_nette_ebitda` | **A** | financials insuffisants (<3 ans / provider muet) |
| structurée | valorisation actuelle | `valuation.prix_actuel` · `relatif.multiple` · `base_rate_anchor` | A / B+ | prix marché ou multiples indisponibles |
| **qualitative** | produits & proposition | `business_model.description` · `unit_economics` | B+ | proposition de valeur non documentée |
| qualitative | positionnement concurrentiel | `moat.preuves[].fait` · `industry.position_vs_pairs` | B+ | dynamique concurrentielle / part vs pairs absente |
| qualitative | structure & état du marché | `industry.croissance_marche_historique_pct` · `structure_5forces` | B+ | marché non documenté |
| qualitative | **management & allocation** (finding #1) | `management.incitations` · `skin_in_game_pct` (+ `management.source_entry_refs`) | A- | allocation du capital non documentée — **empêche désormais un faux `ready`** |
| qualitative | risques principaux | `incertitudes_bloquantes[]` (+ entries `risk`) | B | risques principaux non identifiés |

## Provisionings hors readiness du titre

Deux besoins de données ne sont **pas** gérés par le readiness du ticker :

1. **`position_sizing`** (risk_matrix) — nourri par le **contexte portefeuille** (corrélations,
   exposition sectorielle agrégée, coût d'opportunité — A8), pas par la KB du titre.
2. **Recherche divergente du bear** (bull/bear) — provisionnée **à l'analyse** (A6), pas pré-gatée :
   c'est le mandat de falsification qui crée ses propres entries.

## Ancrage

- Cartes de provenance : `provenance-viz/index.html` (visuel) + §8 de `01-spec-v2-unifiee.md`.
- Pydantic vérifié (pydantic 2.13.4, container backend) : `analysis_v2_schemas.py`.
- Curator / readiness / gaps / thin_qualitative : §7 de `01-spec-v2-unifiee.md` (Q5).
